"""Face detection via OpenCV's YuNet.

cv2 is imported lazily (see vision/pyproject.toml) so `vision.detection`
stays importable without OpenCV installed.

Known integration risk (see docs/architecture.md "Riesgos conocidos"):
JetPack 4.6 ships OpenCV 4.1.1, which predates the `cv2.FaceDetectorYN`
API (needs OpenCV >= 4.5.4). This wrapper assumes a DNN-capable OpenCV
build is present; if that API is missing, either install a newer OpenCV
build for the Jetson (e.g. a Qengineering prebuilt wheel) or replace this
wrapper's internals with a manual `cv2.dnn.readNetFromONNX` + hand-rolled
YuNet decode/NMS. Treat that as a dedicated milestone, not a fallback to
silently swallow here.
"""

import threading
from typing import List, NamedTuple, Tuple

from vision.config import DetectionConfig


class Detection(NamedTuple):
    # (x, y, w, h) in pixels, origin top-left.
    bbox: Tuple[float, float, float, float]
    # 5 (x, y) landmarks: left eye, right eye, nose tip, left mouth, right mouth.
    landmarks: Tuple[Tuple[float, float], ...]
    score: float

    @property
    def center(self):
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)

    @property
    def area(self):
        return self.bbox[2] * self.bbox[3]


class YuNetDetector(object):
    def __init__(self, config=None, frame_size=(640, 480)):
        import cv2  # noqa: local import, see module docstring

        if not hasattr(cv2, "FaceDetectorYN_create") and not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError(
                "this OpenCV build has no FaceDetectorYN — see this module's "
                "docstring for the JetPack 4.6 / OpenCV 4.1.1 upgrade path"
            )

        self._config = config or DetectionConfig()
        self._cv2 = cv2
        self._frame_size = frame_size
        # Guards `_frame_size` + the underlying cv2 net across `detect()`
        # calls: the live pipeline thread and an in-flight enrollment
        # request both call `.detect()` on this same instance (see
        # app/backend/routers/people.py's `_new_enrollment_session`), and
        # `setInputSize()` followed by `.detect()` is not atomic. Without
        # this lock, two frames of different shapes racing here corrupt
        # the net's expected input shape (observed as an OpenCV DNN
        # "Shape mismatch"/`forwardGraph` assertion crashing the pipeline
        # thread).
        self._lock = threading.Lock()
        create = getattr(cv2, "FaceDetectorYN_create", None) or cv2.FaceDetectorYN.create
        self._detector = create(
            self._config.model_path,
            "",
            frame_size,
            self._config.score_threshold,
            self._config.nms_threshold,
            self._config.top_k,
        )

    def set_frame_size(self, width, height):
        if (width, height) != self._frame_size:
            self._frame_size = (width, height)
            self._detector.setInputSize(self._frame_size)

    def detect(self, frame):
        """Returns a list of Detection, largest-area first (MVP: single-face
        tracking picks detections[0] as the target — see AGENTS.md)."""
        height, width = frame.shape[:2]
        with self._lock:
            self.set_frame_size(width, height)
            _, faces = self._detector.detect(frame)
        if faces is None:
            return []

        detections = []
        for row in faces:
            bbox = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
            landmarks = tuple(
                (float(row[4 + 2 * i]), float(row[5 + 2 * i])) for i in range(5)
            )
            score = float(row[14])
            detections.append(Detection(bbox=bbox, landmarks=landmarks, score=score))

        detections.sort(key=lambda d: d.area, reverse=True)
        return detections
