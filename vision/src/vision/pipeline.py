"""Background-thread orchestrator: capture -> detect -> recognize -> track.

One iteration feeds three consumers from a single pass (see
docs/architecture.md's end-to-end flow):
  1. a `move_delta` command to the ESP32 (tracking correction)
  2. the latest annotated JPEG frame (for the MJPEG endpoint)
  3. a structured event (bbox/name/telemetry) for WebSocket subscribers

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

UNKNOWN_LABEL = "Unknown"


class _LabelCache(object):
    """Smooths recognition output so the label doesn't flicker between a
    name and "Unknown" between the sparse frames recognition runs on."""

    def __init__(self, decay_frames):
        self._decay_frames = decay_frames
        self._name = None
        self._remaining = 0

    def update_from_match(self, match):
        if match is not None:
            self._name = match.name
            self._remaining = self._decay_frames
        elif self._remaining > 0:
            self._remaining -= 1
        else:
            self._name = None

    def current(self):
        return self._name if self._remaining > 0 else None


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
        self._config = config or PipelineConfig()
        self._repository = repository or FaceRepository(self._config.storage)
        self.state = SharedState()

        self._tracking_controller = TrackingController(self._config.tracking)
        self._serial_link = SerialLink(self._config.serial_link)
        self._label_cache = _LabelCache(self._config.recognition.label_decay_frames)

        self._tracking_enabled = True
        self._frame_count = 0
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

    def _run(self):
        import cv2  # noqa: local import, see module docstring

        self._camera = Camera(self._config.camera)
        self._detector = YuNetDetector(self._config.detection)
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
            frame = self._camera.read()
            if frame is None:
                time.sleep(0.05)
                continue

            self._process_frame(cv2, frame)

    def _process_frame(self, cv2, frame):
        self._frame_count += 1
        height, width = frame.shape[:2]
        detections = self._detector.detect(frame)
        target = detections[0] if detections else None

        match = None
        if target is not None and self._embedder is not None:
            due = self._frame_count % self._config.recognition.run_every_n_frames == 0
            if due:
                try:
                    embedding = self._embedder.embed_from_landmarks(frame, target.landmarks)
                    match = self._repository.find_best_match(
                        embedding, self._config.recognition.match_threshold
                    )
                except ValueError:
                    match = None
                self._label_cache.update_from_match(match)

        label = self._label_cache.current() or UNKNOWN_LABEL if target is not None else None

        telemetry = self._serial_link.last_telemetry
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

        annotated = self._annotate(cv2, frame, target, label)
        ok, buf = cv2.imencode(".jpg", annotated)
        jpeg = buf.tobytes() if ok else None

        event = {
            "detection": None
            if target is None
            else {
                "bbox": list(target.bbox),
                "score": target.score,
                "label": label,
            },
            "telemetry": None
            if telemetry is None
            else {
                "ok": telemetry.ok,
                "pan_deg": telemetry.pan_deg,
                "tilt_deg": telemetry.tilt_deg,
                "moving": telemetry.moving,
                "homed": telemetry.homed,
            },
            "serial_connected": self._serial_link.connected,
            "tracking_enabled": self._tracking_enabled,
        }
        self.state.publish(jpeg, event)

    def _annotate(self, cv2, frame, target, label):
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        cv2.line(annotated, (width // 2, 0), (width // 2, height), (60, 60, 60), 1)
        cv2.line(annotated, (0, height // 2), (width, height // 2), (60, 60, 60), 1)

        if target is not None:
            x, y, w, h = [int(v) for v in target.bbox]
            color = (0, 255, 0) if label and label != UNKNOWN_LABEL else (0, 165, 255)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            if label:
                cv2.putText(
                    annotated,
                    label,
                    (x, max(0, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )
        return annotated
