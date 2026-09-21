"""Guided 3-photo enrollment capture: front, left, right (RF-1, RF-2, RF-4,
RF-5, RF-6).

An `EnrollmentSession` is purely in-memory and ephemeral: nothing is
persisted until the caller (app/backend/routers/people.py) takes the
accepted (pose, embedding, photo_bytes) triples returned by `finalize()`
and writes them through `FaceRepository`. Abandoning a session (letting it
go out of scope, or calling `cancel()`) leaves zero trace, which is how
RF-6 ("alta abandonada no deja registro parcial") is satisfied without any
database transaction/rollback machinery.

The session takes an already-decoded frame (see `decode_image`), not raw
bytes, so it stays testable with a fake detector/embedder and no cv2
dependency — decoding happens once at the API boundary.
"""

import logging

from vision.config import RecognitionConfig
from vision.recognition.similarity import cosine_similarity

logger = logging.getLogger(__name__)

POSE_ORDER = ("front", "left", "right")


class NoFaceDetected(Exception):
    """Raised when a submitted photo has no detectable face (RF-4)."""


class MultipleFacesDetected(Exception):
    """Raised when a submitted photo has more than one detectable face (RF-4)."""


class SessionAlreadyComplete(Exception):
    """Raised when `capture()` is called after all 3 poses are accepted."""


class SessionIncomplete(Exception):
    """Raised when `finalize()` is called before all 3 poses are accepted."""


class InconsistentPhotos(Exception):
    """Raised at `finalize()` when the 3 accepted photos don't look like the
    same person at >= `enrollment_consistency_threshold` (RF-5)."""


def decode_image(image_bytes):
    """Decodes raw bytes (e.g. a browser canvas.toBlob capture) into a BGR
    frame. Raises NoFaceDetected if the bytes aren't a decodable image."""
    import cv2
    import numpy as np

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise NoFaceDetected("could not decode image")
    return frame


class EnrollmentSession(object):
    def __init__(self, detector, embedder, config=None):
        self._detector = detector
        self._embedder = embedder
        self._config = config or RecognitionConfig()
        self._captures = []  # list of (pose, embedding, photo_bytes)

    @property
    def next_pose(self):
        """The pose (front/left/right) the next `capture()` call will
        record, or None if the session already has all 3 photos."""
        if self.is_complete:
            return None
        return POSE_ORDER[len(self._captures)]

    @property
    def is_complete(self):
        return len(self._captures) >= len(POSE_ORDER)

    def capture(self, frame, photo_bytes=None):
        """Validates the current pose's photo and, if accepted, records it.

        Returns the pose it was recorded as. Raises NoFaceDetected or
        MultipleFacesDetected (RF-4) without changing session state, so the
        caller can ask the user to retake the same pose.
        """
        if self.is_complete:
            raise SessionAlreadyComplete("enrollment session already has 3 photos")

        detections = self._detector.detect(frame)
        if not detections:
            raise NoFaceDetected("no face detected in photo")
        if len(detections) > 1:
            raise MultipleFacesDetected("more than one face detected in photo")

        target = detections[0]
        embedding = self._embedder.embed_from_landmarks(frame, target.landmarks)
        pose = self.next_pose
        self._captures.append((pose, embedding, photo_bytes))
        return pose

    def cancel(self):
        """Discards all captured photos (RF-6, and RF-8's edit-photos cancel)."""
        self._captures = []

    def finalize(self):
        """Validates cross-photo consistency (RF-5) and returns the 3
        accepted (pose, embedding, photo_bytes) triples for the caller to
        persist. Raises SessionIncomplete or InconsistentPhotos instead —
        in both cases nothing is left for the caller to persist, and the
        session is cleared as if `cancel()` had been called.
        """
        if not self.is_complete:
            raise SessionIncomplete("enrollment session needs 3 accepted photos")

        embeddings = [embedding for _, embedding, _ in self._captures]
        poses = [pose for pose, _, _ in self._captures]
        threshold = self._config.enrollment_consistency_threshold
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                logger.warning(
                    "enrollment consistency check %s vs %s: cosine=%.4f (threshold=%.2f)",
                    poses[i], poses[j], sim, threshold,
                )
                if sim < threshold:
                    self.cancel()
                    raise InconsistentPhotos(
                        "the 3 photos do not appear to be the same person"
                    )

        captures = list(self._captures)
        self.cancel()
        return captures
