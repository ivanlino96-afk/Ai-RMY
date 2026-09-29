"""Background-thread orchestrator: capture -> detect -> recognize -> track.

One iteration feeds three consumers from a single pass (see
docs/architecture.md's end-to-end flow):
  1. a `move_delta` command to the Arduino MKR Zero (tracking correction, largest face)
  2. the latest annotated JPEG frame (for the MJPEG endpoint)
  3. a structured event (all detections/name-or-Desconocido/telemetry) for
     WebSocket subscribers

This is why `app/backend` imports this package in-process instead of
calling it as a separate service: the video the operator watches and the
detection driving the gimbal must come from the same frame.

cv2 is imported lazily at the top of run() (not at module load) so this
module is importable — e.g. for type-checking or wiring the FastAPI app
before the CV stack is confirmed installed — without OpenCV present.
"""

import collections
import logging
import os
import threading
import time
import uuid

from vision.capture.camera import Camera, list_available_cameras
from vision.config import PipelineConfig, validate_scan_config
from vision.motor_settings import MotorSettings, StepLimits
from vision.detection.objects import ObjectDetector
from vision.detection.yunet import YuNetDetector
from vision.recognition.embedder import FaceEmbedder
from vision.serial_link.client import SerialLink
from vision.storage.repository import FaceRepository
from vision.tracking.controller import PixelOffset, TrackingController

logger = logging.getLogger(__name__)

# RF-13: "Desconocido" in Spanish, not "Unknown" -- this is a user-facing
# label the frontend renders verbatim, not an internal identifier.
UNKNOWN_LABEL = "Desconocido"

# Observed repeatedly on Windows: a freshly-opened VideoCapture reports
# isOpened() True immediately, but every read() fails for a while -- and
# occasionally forever, until the same index is released and reopened once
# more in the same process. Past this many consecutive failed reads on an
# open camera, _maybe_reopen_stuck_camera() forces exactly that reopen
# instead of leaving the operator staring at "connecting..." forever.
# ~1s at _run_once's 50ms post-failure sleep.
_CAMERA_WARMUP_MAX_FAILED_READS = 20


def _center_distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _frange_inclusive(lo, hi, step):
    """[lo, hi] stepped by `step`, always including `hi` exactly even if it
    isn't an exact multiple of `step` past `lo` (so a scan's edge is never
    silently skipped)."""
    values = []
    v = lo
    while v <= hi + 1e-6:
        values.append(round(v, 3))
        v += step
    if not values or values[-1] < hi - 1e-6:
        values.append(hi)
    return values


def _build_scan_waypoints(scan_config):
    """Row-major pan/tilt grid: a 2D angular inventory, not a 3D map (see
    AGENTS.md's rule against claiming absolute position without homing --
    this only ever records "object seen at pan deg/tilt deg")."""
    if scan_config.step_deg <= 0:
        return []
    pan_lo, pan_hi = scan_config.pan_range_deg
    tilt_lo, tilt_hi = scan_config.tilt_range_deg
    pans = _frange_inclusive(pan_lo, pan_hi, scan_config.step_deg)
    tilts = _frange_inclusive(tilt_lo, tilt_hi, scan_config.step_deg)
    return [(pan, tilt) for tilt in tilts for pan in pans]


class _IdentityMemory(object):
    """Per-face recognized-identity memory with a time window (RF-14).

    Recognition only runs every `run_every_n_frames`-th frame (it's far
    more expensive than detection), so between those frames -- and across
    a face briefly leaving and re-entering the frame -- this remembers the
    last label seen for the closest face position, for up to
    `window_seconds`. Past that window a reappearing face is evaluated as
    a brand new detection, per RF-14's second clause.

    Faces are correlated across frames by nearest bbox-center distance:
    this codebase has no persistent multi-object tracker, and proximity is
    the simplest signal available for "is this the same face as before".
    """

    def __init__(self, window_seconds, max_center_distance=75.0, time_fn=time.time):
        self._window_seconds = window_seconds
        self._max_center_distance = max_center_distance
        self._time_fn = time_fn
        self._entries = []

    def remember(self, center, label, now=None):
        now = self._time_fn() if now is None else now
        entry = self._closest(center, now)
        if entry is None:
            entry = {}
            self._entries.append(entry)
        entry["center"] = center
        entry["label"] = label
        entry["last_seen"] = now

    def recall(self, center, now=None):
        """Returns (label, found). `found` is False if no still-fresh entry
        is close enough to `center` -- the caller should treat that as an
        unevaluated face, not assume "Desconocido"."""
        now = self._time_fn() if now is None else now
        entry = self._closest(center, now)
        if entry is None:
            return None, False
        return entry["label"], True

    def _closest(self, center, now):
        best = None
        best_dist = None
        for entry in self._entries:
            if now - entry["last_seen"] > self._window_seconds:
                continue
            dist = _center_distance(center, entry["center"])
            if dist <= self._max_center_distance and (best_dist is None or dist < best_dist):
                best = entry
                best_dist = dist
        return best


class SharedState(object):
    """Thread-safe latest-frame/latest-event holder with change notification
    for WebSocket-style consumers (push, not poll)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._jpeg = None
        self._event = None
        self._version = 0

    def publish(self, jpeg, event):
        with self._condition:
            self._jpeg = jpeg
            self._event = event
            self._version += 1
            self._condition.notify_all()

    def latest_jpeg(self):
        with self._lock:
            return self._jpeg

    def latest_event(self):
        with self._lock:
            return self._event

    def wait_for_update(self, last_version, timeout=None):
        """Blocks until a version newer than `last_version` is published.

        Returns (event, version). Used by the WebSocket endpoint so it
        pushes on change instead of polling.
        """
        with self._condition:
            if self._version == last_version:
                self._condition.wait(timeout=timeout)
            return self._event, self._version


class Pipeline(object):
    def __init__(self, config=None, repository=None):
        self.config = config or PipelineConfig()
        self._config = self.config
        self._repository = repository or FaceRepository(self._config.storage)
        self.state = SharedState()

        self._tracking_controller = TrackingController(self._config.tracking)
        self._serial_link = SerialLink(self._config.serial_link)
        settings_path = (os.path.join(os.path.dirname(self._config.storage.db_path), "motor-speeds.json")
                         if self._config.storage.db_path != ":memory:" else None)
        self.motor_settings = MotorSettings(settings_path)
        self.step_limits = StepLimits(os.path.join(os.path.dirname(settings_path), "step-limits.json") if settings_path else None)
        self._identity_memory = _IdentityMemory(self._config.recognition.identity_memory_seconds)

        self._tracking_enabled = True
        self._frame_count = 0
        self._camera_connected = True
        self._stop_event = threading.Event()
        self._thread = None

        # Created lazily in run() once we're on the worker thread, since
        # they touch cv2/onnxruntime/the camera device.
        self._camera = None
        self._detector = None
        self._embedder = None
        self._object_detector = None

        # Room-scan / angular object inventory state (see specs/tasks.md).
        # Guarded by _scan_lock since start_scan()/cancel_scan()/scan_status()
        # are called from request-handling threads while _service_scan() runs
        # on the worker thread -- same "request threads + worker thread share
        # state under a lock" shape as camera selection below.
        self._scan_lock = threading.Lock()
        self._scan_active = False
        self._scan_state = "idle"  # idle | running | done
        self._scan_config = None
        self._scan_waypoints = []
        self._scan_index = 0
        self._scan_results = []
        self._scan_waypoint_sent = False
        self._scan_waypoint_started_at = None
        self._scan_waypoint_arrived_at = None

        # Defense mode / threat alarm state (see AGENTS.md's scope section).
        # Guarded by _defense_lock for the same reason as _scan_lock above:
        # start_defense_mode()/stop_defense_mode()/defense_status() are
        # called from request-handling threads while _service_defense() runs
        # on the worker thread.
        self._defense_lock = threading.Lock()
        self._defense_active = False
        self._defense_armed_at = None
        self._pre_defense_tracking_enabled = True
        self._defense_sightings = []
        self._recent_alarm_photos = []
        self._defense_log = collections.deque(maxlen=self._config.defense.log_max_events)

        # No camera is opened at startup -- the frontend enumerates devices
        # and calls select_camera() once the operator picks one. Guarded by
        # _camera_lock since select_camera() is called from request-handling
        # threads while _sync_camera() runs on the worker thread.
        self._camera_index = None
        self._requested_camera_index = None
        self._camera_generation = 0
        self._applied_camera_generation = 0
        self._camera_lock = threading.Lock()
        self._camera_fail_count = 0

    def start(self):
        self._serial_link.start()
        self._thread = threading.Thread(target=self._run, name="vision-pipeline", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._serial_link.stop()
        if self._camera is not None:
            self._camera.release()

    def set_tracking_enabled(self, enabled):
        """Returns False (no-op) if asked to enable while a scan owns the
        gimbal -- auto-tracking must never race a scan's own goto sequence.
        Also refuses to disable while defense mode is armed -- defense mode
        forces tracking on for as long as it's active; disarm it instead."""
        if enabled and (self._scan_active or
                        (self.last_telemetry is not None and self.last_telemetry.calibration)):
            return False
        if not enabled and self._defense_active:
            return False
        self._tracking_enabled = enabled
        if not enabled:
            self._serial_link.send_stop()
        return True

    def _motion_profile(self, name):
        profile = self.motor_settings.get(name)
        profile.update(self.step_limits.get("limits"))
        return profile

    def jog_steps(self, pan_steps, tilt_steps):
        telemetry = self.last_telemetry
        if (self._tracking_enabled or self._scan_active or self._defense_active or
                not self.serial_connected or telemetry is None or
                telemetry.moving):
            return False
        limits = self.step_limits.get("limits")
        if not (limits["pan_min"] <= telemetry.pan_steps + pan_steps <= limits["pan_max"] and
                limits["tilt_min"] <= telemetry.tilt_steps + tilt_steps <= limits["tilt_max"]):
            return False
        profile = self.motor_settings.get("manual")
        profile.update(limits)
        return self._serial_link.send_move_steps(pan_steps, tilt_steps, speeds=profile)

    def center(self):
        self._serial_link.send_goto(0.0, 0.0, speeds=self._motion_profile("manual"))

    def home(self):
        """No limit switches: re-defines the gimbal's current physical
        position as the new (0,0) origin. Does not move any motor -- see
        AGENTS.md."""
        self._serial_link.send_home()

    def jog(self, pan_deg=0.0, tilt_deg=0.0):
        """Manual per-axis nudge for bench-testing motors (manual mode).

        Refuses while tracking is enabled so a manual jog never races the
        auto-tracker's own move_delta calls -- mirrors the gate already
        applied in _process_frame."""
        if self._tracking_enabled:
            return False
        self._serial_link.send_move_delta(pan_deg, tilt_deg, speeds=self._motion_profile("manual"))
        return True

    def emergency_stop(self):
        """Manual mode: cut any motion in progress, independent of tracking
        state -- unlike jog(), this must always work (see AGENTS.md: "stop
        tiene la máxima prioridad"). Also cancels an in-progress scan and
        disarms defense mode, since both are series of motions in progress."""
        self._serial_link.send_stop()
        self.cancel_scan()
        self.stop_defense_mode()

    def start_scan(self, pan_range_deg=None, tilt_range_deg=None, step_deg=None):
        """Requests a room-scan sweep. Refuses (returns False) while tracking
        is enabled or another scan is already running -- serviced afterward,
        one waypoint per _run_once tick, by _service_scan()."""
        with self._scan_lock:
            if (self._tracking_enabled or self._scan_active or
                    (self.last_telemetry is not None and self.last_telemetry.calibration)):
                return False
            scan_config = self._config.scan
            if pan_range_deg is not None:
                scan_config = scan_config._replace(pan_range_deg=tuple(pan_range_deg))
            if tilt_range_deg is not None:
                scan_config = scan_config._replace(tilt_range_deg=tuple(tilt_range_deg))
            if step_deg is not None:
                scan_config = scan_config._replace(step_deg=step_deg)
            scan_config = validate_scan_config(scan_config)

            waypoints = _build_scan_waypoints(scan_config)
            if not waypoints:
                return False

            self._scan_config = scan_config
            self._scan_waypoints = waypoints
            self._scan_index = 0
            self._scan_results = []
            self._scan_waypoint_sent = False
            self._scan_waypoint_started_at = None
            self._scan_waypoint_arrived_at = None
            self._scan_active = True
            self._scan_state = "running"
            return True

    def cancel_scan(self):
        with self._scan_lock:
            was_active = self._scan_active
            self._scan_active = False
            self._scan_state = "idle"
        if was_active:
            self._serial_link.send_stop()

    def scan_status(self):
        with self._scan_lock:
            total = len(self._scan_waypoints)
            progress = (self._scan_index / float(total)) if total else 0.0
            return {
                "state": self._scan_state,
                "progress": progress,
                "results": list(self._scan_results),
            }

    def start_defense_mode(self):
        """Arms defense mode: forces tracking on and makes _select_target
        prioritize an unrecognized face over a recognized one. Refuses
        (returns False) while a room scan is running -- both need exclusive
        use of the gimbal."""
        with self._defense_lock:
            if (self._defense_active or
                    (self.last_telemetry is not None and self.last_telemetry.calibration)):
                return False
            if self._scan_active:
                return False
            self._pre_defense_tracking_enabled = self._tracking_enabled
            self._tracking_enabled = True
            self._defense_active = True
            self._defense_armed_at = time.time()
            self._defense_sightings = []
            self._recent_alarm_photos = []
            return True

    def stop_defense_mode(self):
        """Disarms defense mode and restores tracking to whatever it was set
        to before arming. Always safe to call, armed or not (mirrors
        cancel_scan())."""
        with self._defense_lock:
            if not self._defense_active:
                return
            self._defense_active = False
            self._defense_armed_at = None
            self._defense_sightings = []
            self._recent_alarm_photos = []
            restore = self._pre_defense_tracking_enabled
        self._tracking_enabled = restore
        if not restore:
            self._serial_link.send_stop()

    def defense_status(self):
        with self._defense_lock:
            return {
                "active": self._defense_active,
                "armed_at": self._defense_armed_at,
                "log": list(self._defense_log),
            }

    @property
    def tracking_enabled(self):
        return self._tracking_enabled

    @property
    def serial_connected(self):
        return self._serial_link.connected

    @property
    def last_telemetry(self):
        return self._serial_link.last_telemetry

    @property
    def detector(self):
        """None until the worker thread finishes its cv2/camera setup, or if
        that setup failed -- callers (e.g. the enrollment API) must treat
        None as "recognition stack unavailable", not assume it's ready."""
        return self._detector

    @property
    def embedder(self):
        return self._embedder

    @property
    def camera_index(self):
        """The currently-open device index, or None if no camera is selected
        or the last selection failed to open."""
        return self._camera_index

    def list_cameras(self):
        """Probes device indices for available cameras.

        Holds `_camera_lock` for the whole probe -- on Windows, opening a
        device index while `_sync_camera()` is mid-open on that same index
        (from another thread) can make the underlying VideoCapture backend
        (DSHOW) throw and fail the real open. Serializing the two makes that
        impossible instead of merely unlikely.
        """
        with self._camera_lock:
            return list_available_cameras()

    def select_camera(self, device_index):
        """Requests that the worker thread (re)open `device_index`. Picked up
        by `_sync_camera()` on its next loop tick -- never blocks, and a
        failed open never kills the pipeline thread (see _sync_camera)."""
        with self._camera_lock:
            self._requested_camera_index = device_index
            self._camera_generation += 1

    def _run(self):
        try:
            import cv2  # noqa: local import, see module docstring
        except Exception:
            logger.exception("vision pipeline disabled: OpenCV (cv2) is not installed")
            return

        try:
            self._detector = YuNetDetector(self._config.detection)
        except Exception:
            logger.exception(
                "vision pipeline disabled: face detector unavailable "
                "(no CV-capable OpenCV build) — API endpoints still work, "
                "but video/tracking will not run"
            )
            return

        try:
            self._embedder = FaceEmbedder(self._config.recognition)
        except Exception:
            logger.exception(
                "face embedder unavailable — recognition disabled, "
                "detections will report as %s",
                UNKNOWN_LABEL,
            )
            self._embedder = None

        try:
            self._object_detector = ObjectDetector(self._config.object_detection)
        except Exception:
            logger.exception(
                "object detector unavailable — room-scan object labels "
                "disabled, scans will not start"
            )
            self._object_detector = None

        while not self._stop_event.is_set():
            self._sync_camera()
            self._run_once(cv2)

    def _sync_camera(self):
        """Opens/closes `self._camera` to match the latest select_camera()
        call. A no-op (no cv2 call) unless the requested generation changed,
        so this is cheap to call every loop tick. Never raises -- a camera
        that fails to open just leaves the pipeline with no camera, exactly
        like a disconnect, instead of killing the worker thread the way a
        one-shot startup-only open used to.

        Holds `_camera_lock` for the whole release+open, not just the
        generation check: on Windows, a concurrent list_cameras() probe
        opening the same device index while this is mid-open can make the
        backend (DSHOW) throw and fail this open. select_camera() briefly
        blocks on this lock while that's happening, which is an acceptable
        trade for the open never spuriously failing.
        """
        with self._camera_lock:
            index = self._requested_camera_index
            generation = self._camera_generation
            if generation == self._applied_camera_generation:
                return
            self._applied_camera_generation = generation
            self._camera_fail_count = 0

            if self._camera is not None:
                self._camera.release()
                self._camera = None
            self._camera_index = None

            if index is None:
                return
            try:
                self._camera = Camera(self._config.camera._replace(device_index=index))
                self._camera_index = index
            except Exception:
                logger.exception("vision pipeline: could not open camera index %d", index)

    def _run_once(self, cv2):
        """One `_run()` loop iteration, split out so a single bad frame's
        exception handling is unit-testable without a real camera/cv2
        thread loop (see test_pipeline.py)."""
        frame = self._camera.read() if self._camera is not None else None
        try:
            self._handle_frame(cv2, frame)
            self._service_scan(cv2, frame)
        except Exception:
            # A single bad frame (e.g. a transient detector/DNN error) must
            # not kill this thread permanently -- `state` would then keep
            # serving its last frame/event forever with no way to recover
            # short of restarting the process. Log and keep pulling frames
            # instead.
            logger.exception("vision pipeline: error processing frame, skipping it")
        if frame is None:
            if self._tracking_enabled and not self._scan_active:
                self._serial_link.send_stop()
            time.sleep(0.05)

    def _handle_frame(self, cv2, frame):
        """One iteration's worth of work, split out from `_run()` so it can
        be unit-tested without a real camera/cv2 thread loop.
        """
        if frame is None:
            # RF-16: notify exactly once per connected -> disconnected
            # transition, not once per failed read attempt.
            if self._camera_connected:
                self._camera_connected = False
                self._publish_camera_event(connected=False)
            self._maybe_reopen_stuck_camera()
            return

        # Reconnect (if we were disconnected) is implicitly notified by the
        # normal event this frame publishes below, which carries
        # camera_connected=True.
        self._camera_connected = True
        self._camera_fail_count = 0
        self._process_frame(cv2, frame)

    def _maybe_reopen_stuck_camera(self):
        """Self-heal a camera that opened but has never delivered a frame.

        Observed repeatedly on this Windows dev machine: a freshly-opened
        VideoCapture reports isOpened() True immediately but every read()
        fails for a while -- sometimes forever, until the same index is
        released and reopened once. Rather than leaving the operator staring
        at "connecting..." with no recourse, treat that as a failure after a
        short grace period and reopen automatically.
        """
        if self._camera is None:
            return
        self._camera_fail_count += 1
        if self._camera_fail_count < _CAMERA_WARMUP_MAX_FAILED_READS:
            return
        self._camera_fail_count = 0
        index = self._camera_index
        with self._camera_lock:
            self._camera.release()
            self._camera = None
            self._camera_index = None
            try:
                self._camera = Camera(self._config.camera._replace(device_index=index))
                self._camera_index = index
            except Exception:
                logger.exception(
                    "vision pipeline: could not reopen stuck camera index %d", index
                )

    def _service_scan(self, cv2, frame):
        """One scan step per tick, called right after _handle_frame from the
        same try/except in _run_once -- a bad waypoint (detector error, no
        frame) must not kill the worker thread, same guarantee as a bad
        detection frame."""
        with self._scan_lock:
            if not self._scan_active:
                return
            if self._scan_index >= len(self._scan_waypoints):
                self._scan_active = False
                self._scan_state = "done"
                return

            pan_deg, tilt_deg = self._scan_waypoints[self._scan_index]
            now = time.monotonic()

            if not self._scan_waypoint_sent:
                self._serial_link.send_goto(pan_deg, tilt_deg, speeds=self._motion_profile("automatic"))
                self._scan_waypoint_sent = True
                self._scan_waypoint_started_at = now
                self._scan_waypoint_arrived_at = None
                return

            telemetry = self._serial_link.last_telemetry
            timed_out = now - self._scan_waypoint_started_at >= self._scan_config.arrival_timeout_s
            arrived = timed_out or (telemetry is not None and not telemetry.moving)
            if not arrived:
                return

            if self._scan_waypoint_arrived_at is None:
                self._scan_waypoint_arrived_at = now
                return
            if now - self._scan_waypoint_arrived_at < self._scan_config.dwell_s:
                return

            objects = []
            if self._object_detector is not None and frame is not None:
                objects = self._object_detector.detect(frame)

            self._scan_results.append(
                {
                    "pan_deg": pan_deg,
                    "tilt_deg": tilt_deg,
                    "objects": [
                        {"bbox": list(o.bbox), "label": o.label, "score": o.score}
                        for o in objects
                    ],
                }
            )
            self._scan_index += 1
            self._scan_waypoint_sent = False
            self._scan_waypoint_arrived_at = None
            if self._scan_index >= len(self._scan_waypoints):
                self._scan_active = False
                self._scan_state = "done"

    def _select_target(self, results):
        """Picks the tracking target for this frame.

        Normally the largest face wins (results is sorted largest-first,
        same as the raw detections list). While defense mode is armed, an
        unrecognized ("enemy") face is prioritized over a recognized one
        that's simultaneously in frame, so the gimbal centers the suspect
        instead of a known person standing next to them."""
        if not results:
            return None
        if self._defense_active:
            for detection, label in results:
                if label is None:
                    return detection
        return results[0][0]

    def _service_defense(self, frame, results, now=None):
        """One defense-mode tick, called from _process_frame right after
        `results` (detection, label) pairs are computed for this frame --
        unlike _service_scan, this needs per-frame recognition results, so
        it can't be driven from _run_once alongside _handle_frame.

        Correlates each detection against the last frame's "sightings" by
        bbox-center distance (same criterion as _IdentityMemory), so a
        suspect who stays in frame accumulates a continuous unidentified
        timer, and a suspect who leaves and later reappears starts a fresh
        one (re-arming the alarm's timer). A fresh sighting still won't take
        a new photo if one was already taken nearby within
        `alarm_photo_cooldown_s` -- see `_alarm_photo_suppressed` -- so a
        suspect who lingers with brief in-and-out gaps (head turns, missed
        detection frames) yields one photo per intrusion, not one per gap."""
        now = time.time() if now is None else now
        with self._defense_lock:
            if not self._defense_active:
                return

            config = self._config.defense
            claimed_ids = set()
            for detection, label in results:
                center = detection.center
                sighting = None
                best_dist = None
                for candidate in self._defense_sightings:
                    if id(candidate) in claimed_ids:
                        continue
                    dist = _center_distance(center, candidate["center"])
                    if dist <= config.max_center_distance and (
                        best_dist is None or dist < best_dist
                    ):
                        sighting = candidate
                        best_dist = dist
                if sighting is None:
                    sighting = {
                        "first_unidentified_at": None,
                        "alarm_fired": False,
                        "identified_logged": False,
                    }
                    self._defense_sightings.append(sighting)
                sighting["center"] = center
                sighting["last_seen"] = now
                claimed_ids.add(id(sighting))

                if label is not None:
                    sighting["first_unidentified_at"] = None
                    sighting["alarm_fired"] = False
                    if not sighting["identified_logged"]:
                        sighting["identified_logged"] = True
                        self._append_defense_log("identified", name=label)
                else:
                    sighting["identified_logged"] = False
                    if sighting["first_unidentified_at"] is None:
                        sighting["first_unidentified_at"] = now
                    elapsed = now - sighting["first_unidentified_at"]
                    if elapsed >= config.threat_seconds and not sighting["alarm_fired"]:
                        sighting["alarm_fired"] = True
                        if not self._alarm_photo_suppressed(center, now, config):
                            filename = (
                                self._save_alarm_photo(frame) if frame is not None else None
                            )
                            self._recent_alarm_photos.append({"center": center, "time": now})
                            self._append_defense_log("threat", photo=filename)

            self._defense_sightings = [
                sighting
                for sighting in self._defense_sightings
                if now - sighting["last_seen"] <= config.sighting_timeout_s
            ]

    def _alarm_photo_suppressed(self, center, now, config):
        """True if a threat photo was already taken near `center` within
        `alarm_photo_cooldown_s` -- prevents a suspect who dips in and out of
        detection (past `sighting_timeout_s`, which re-arms the per-sighting
        timer) from generating a fresh photo every time, as long as they
        keep reappearing in roughly the same spot."""
        self._recent_alarm_photos = [
            entry
            for entry in self._recent_alarm_photos
            if now - entry["time"] <= config.alarm_photo_cooldown_s
        ]
        return any(
            _center_distance(center, entry["center"]) <= config.max_center_distance
            for entry in self._recent_alarm_photos
        )

    def _append_defense_log(self, event_type, name=None, photo=None):
        self._defense_log.append(
            {"type": event_type, "timestamp": time.time(), "name": name, "photo": photo}
        )

    def _save_alarm_photo(self, frame):
        """Saves the raw (pre-annotation) frame -- _annotate only draws the
        centering crosshair, so the annotated frame has nothing the suspect
        photo needs and the raw frame is the more useful record."""
        import cv2  # noqa: local import, see module docstring

        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        alarms_dir = self._config.storage.alarms_dir
        os.makedirs(alarms_dir, exist_ok=True)
        filename = "%d_%s.jpg" % (int(time.time()), uuid.uuid4().hex[:8])
        with open(os.path.join(alarms_dir, filename), "wb") as f:
            f.write(buf.tobytes())
        return filename

    def _scan_event_payload(self):
        status = self.scan_status()
        if status["state"] == "idle" and not status["results"]:
            return None
        return status

    def _defense_event_payload(self):
        status = self.defense_status()
        if not status["active"] and not status["log"]:
            return None
        return status

    def _publish_camera_event(self, connected):
        self.state.publish(
            None,
            {
                "frame_width": None,
                "frame_height": None,
                "detections": [],
                "telemetry": self._telemetry_dict(),
                "serial_connected": self._serial_link.connected,
                "tracking_enabled": self._tracking_enabled,
                "camera_connected": connected,
                "camera_index": self._camera_index,
                "scan": self._scan_event_payload(),
                "defense": self._defense_event_payload(),
            },
        )

    def _telemetry_dict(self):
        telemetry = self._serial_link.last_telemetry
        if telemetry is None:
            return None
        return {
            "ok": telemetry.ok,
            "pan_deg": telemetry.pan_deg,
            "tilt_deg": telemetry.tilt_deg,
            "moving": telemetry.moving,
            "homed": telemetry.homed,
        }

    def _process_frame(self, cv2, frame):
        self._frame_count += 1
        height, width = frame.shape[:2]
        detections = self._detector.detect(frame)

        recognition_due = (
            self._embedder is not None
            and self._frame_count % self._config.recognition.run_every_n_frames == 0
        )
        results = [
            (detection, self._label_for(detection, frame, recognition_due))
            for detection in detections
        ]
        self._service_defense(frame, results)

        # Tracking follows a single target -- normally the largest face
        # (detections are sorted largest-first by YuNetDetector.detect), but
        # _select_target prioritizes an unrecognized face while defense mode
        # is armed.
        target = self._select_target(results)
        tracking_offset = None
        if target is not None:
            cx, cy = target.center
            offset = PixelOffset(
                dx=cx - width / 2.0,
                dy=cy - height / 2.0,
                frame_width=width,
                frame_height=height,
            )
            delta = self._tracking_controller.compute(offset)
            tracking_offset = {
                "dx": offset.dx,
                "dy": offset.dy,
                "pan_deg": delta.pan_deg if delta is not None else 0.0,
                "tilt_deg": delta.tilt_deg if delta is not None else 0.0,
                "centered": delta is None,
            }
            # The UI shows this offset/correction regardless of whether
            # tracking is paused, but the Arduino MKR Zero only moves while enabled.
            if delta is not None and self._tracking_enabled and not self._scan_active:
                self._serial_link.send_move_delta(delta.pan_deg, delta.tilt_deg, speeds=self._motion_profile("automatic"))

        # Hold when the face is centered or lost; do not finish a stale correction.
        if self._tracking_enabled and not self._scan_active and (target is None or tracking_offset["centered"]):
            telemetry = self.last_telemetry
            if telemetry is not None and telemetry.moving:
                self._serial_link.send_stop()

        annotated = self._annotate(cv2, frame)
        ok, buf = cv2.imencode(".jpg", annotated)
        jpeg = buf.tobytes() if ok else None

        event = {
            "frame_width": width,
            "frame_height": height,
            "detections": [
                {
                    "bbox": list(detection.bbox),
                    "score": detection.score,
                    "label": label or UNKNOWN_LABEL,
                }
                for detection, label in results
            ],
            "telemetry": self._telemetry_dict(),
            "serial_connected": self._serial_link.connected,
            "tracking_enabled": self._tracking_enabled,
            "camera_connected": True,
            "camera_index": self._camera_index,
            "tracking_offset": tracking_offset,
            "scan": self._scan_event_payload(),
            "defense": self._defense_event_payload(),
        }
        self.state.publish(jpeg, event)

    def _label_for(self, detection, frame, recognition_due):
        """RF-11/RF-18: each detected face is matched independently against
        every registered person; the highest-scoring match >= threshold
        wins. Returns None for "no match" (displayed as Desconocido)."""
        center = detection.center

        if not recognition_due:
            label, found = self._identity_memory.recall(center)
            return label if found else None

        try:
            embedding = self._embedder.embed_from_landmarks(frame, detection.landmarks)
            matches = self._repository.find_all_matches(
                embedding, self._config.recognition.match_threshold
            )
        except ValueError:
            matches = []

        label = matches[0].name if matches else None
        self._identity_memory.remember(center, label)
        return label

    def _annotate(self, cv2, frame):
        # RF-12/RF-13 (box + label per face) is rendered once, client-side, by
        # DetectionOverlay -- it has the match score to show, this layer
        # doesn't. Drawing it here too used to double up every face with a
        # second, unlabelled box baked into the MJPEG stream.
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        cv2.line(annotated, (width // 2, 0), (width // 2, height), (60, 60, 60), 1)
        cv2.line(annotated, (0, height // 2), (width, height // 2), (60, 60, 60), 1)
        return annotated
