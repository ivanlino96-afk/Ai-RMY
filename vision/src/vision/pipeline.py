"""Background-thread orchestrator: capture -> detect -> recognize -> track.

One iteration feeds three consumers from a single pass (see
docs/architecture.md's end-to-end flow):
  1. a `move_delta` command to the ESP32 (tracking correction, largest face)
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

import logging
import threading
import time

from vision.capture.camera import Camera
from vision.config import PipelineConfig
from vision.detection.yunet import YuNetDetector
from vision.recognition.embedder import FaceEmbedder
from vision.serial_link.client import SerialLink
from vision.storage.repository import FaceRepository
from vision.tracking.controller import PixelOffset, TrackingController

logger = logging.getLogger(__name__)

# RF-13: "Desconocido" in Spanish, not "Unknown" -- this is a user-facing
# label the frontend renders verbatim, not an internal identifier.
UNKNOWN_LABEL = "Desconocido"

_KNOWN_COLOR = (0, 255, 0)  # BGR green -- recognized match, RF-12
_UNKNOWN_COLOR = (0, 0, 255)  # BGR red -- no match >= threshold, RF-13


def _center_distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


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
        self._tracking_enabled = enabled
        if not enabled:
            self._serial_link.send_stop()

    def center(self):
        self._serial_link.send_goto(0.0, 0.0)

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

    def _run(self):
        try:
            import cv2  # noqa: local import, see module docstring

            self._camera = Camera(self._config.camera)
            self._detector = YuNetDetector(self._config.detection)
        except Exception:
            logger.exception(
                "vision pipeline disabled: camera/detector unavailable "
                "(missing cv2, no CV-capable OpenCV build, or no camera "
                "device) — API endpoints still work, but video/tracking "
                "will not run"
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

        while not self._stop_event.is_set():
            self._run_once(cv2)

    def _run_once(self, cv2):
        """One `_run()` loop iteration, split out so a single bad frame's
        exception handling is unit-testable without a real camera/cv2
        thread loop (see test_pipeline.py)."""
        frame = self._camera.read()
        try:
            self._handle_frame(cv2, frame)
        except Exception:
            # A single bad frame (e.g. a transient detector/DNN error) must
            # not kill this thread permanently -- `state` would then keep
            # serving its last frame/event forever with no way to recover
            # short of restarting the process. Log and keep pulling frames
            # instead.
            logger.exception("vision pipeline: error processing frame, skipping it")
        if frame is None:
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
            return

        # Reconnect (if we were disconnected) is implicitly notified by the
        # normal event this frame publishes below, which carries
        # camera_connected=True.
        self._camera_connected = True
        self._process_frame(cv2, frame)

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

        # Tracking still follows a single target -- the largest face
        # (detections are sorted largest-first by YuNetDetector.detect).
        target = detections[0] if detections else None
        if target is not None and self._tracking_enabled:
            cx, cy = target.center
            offset = PixelOffset(
                dx=cx - width / 2.0,
                dy=cy - height / 2.0,
                frame_width=width,
                frame_height=height,
            )
            delta = self._tracking_controller.compute(offset)
            if delta is not None:
                self._serial_link.send_move_delta(delta.pan_deg, delta.tilt_deg)

        annotated = self._annotate(cv2, frame, results)
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

    def _annotate(self, cv2, frame, results):
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        cv2.line(annotated, (width // 2, 0), (width // 2, height), (60, 60, 60), 1)
        cv2.line(annotated, (0, height // 2), (width, height // 2), (60, 60, 60), 1)

        for detection, label in results:
            x, y, w, h = [int(v) for v in detection.bbox]
            color = _KNOWN_COLOR if label else _UNKNOWN_COLOR
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                annotated,
                label or UNKNOWN_LABEL,
                (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )
        return annotated
