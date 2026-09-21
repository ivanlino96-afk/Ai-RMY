import numpy as np
import pytest

from vision.config import RecognitionConfig
from vision.detection.yunet import Detection
from vision.enroll import (
    EnrollmentSession,
    InconsistentPhotos,
    MultipleFacesDetected,
    NoFaceDetected,
    SessionIncomplete,
)

_LANDMARKS = ((0.0, 0.0), (10.0, 0.0), (5.0, 5.0), (0.0, 10.0), (10.0, 10.0))


def _detection():
    return Detection(bbox=(0.0, 0.0, 20.0, 20.0), landmarks=_LANDMARKS, score=0.99)


class FakeDetector(object):
    def __init__(self, detections):
        self._detections = detections

    def detect(self, frame):
        return self._detections


class FakeEmbedder(object):
    def __init__(self, vector):
        self._vector = np.asarray(vector, dtype=np.float32)

    def embed_from_landmarks(self, frame, landmarks):
        return self._vector


def make_session(detections=None, vector=None, config=None):
    detector = FakeDetector([_detection()] if detections is None else detections)
    embedder = FakeEmbedder(np.ones(4, dtype=np.float32) if vector is None else vector)
    return EnrollmentSession(detector, embedder, config=config or RecognitionConfig())


def test_capture_rejects_photo_with_no_face():
    session = make_session(detections=[])
    with pytest.raises(NoFaceDetected):
        session.capture(frame="fake-frame")
    assert session.next_pose == "front"


def test_capture_rejects_photo_with_two_faces():
    session = make_session(detections=[_detection(), _detection()])
    with pytest.raises(MultipleFacesDetected):
        session.capture(frame="fake-frame")
    assert session.next_pose == "front"


def test_abandoned_session_persists_nothing():
    session = make_session()
    session.capture(frame="fake-frame")
    assert session.next_pose == "left"
    # Abandoned mid-way: never finalized, and cancel() (what an API DELETE
    # would call) leaves no captures behind.
    session.cancel()
    assert session.next_pose == "front"
    assert session.is_complete is False


def test_full_session_in_correct_pose_order_accepts_all_three():
    session = make_session()
    assert session.capture(frame="fake-frame") == "front"
    assert session.capture(frame="fake-frame") == "left"
    assert session.capture(frame="fake-frame") == "right"
    assert session.is_complete is True

    captures = session.finalize()
    assert [pose for pose, _, _ in captures] == ["front", "left", "right"]


def test_finalize_before_complete_raises():
    session = make_session()
    session.capture(frame="fake-frame")
    with pytest.raises(SessionIncomplete):
        session.finalize()


def test_finalize_rejects_inconsistent_photos():
    detector = FakeDetector([_detection()])
    vectors = [
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),  # orthogonal outlier
    ]

    class SequentialEmbedder(object):
        def __init__(self, vectors):
            self._vectors = list(vectors)

        def embed_from_landmarks(self, frame, landmarks):
            return self._vectors.pop(0)

    session = EnrollmentSession(detector, SequentialEmbedder(vectors), config=RecognitionConfig())
    session.capture(frame="fake-frame")
    session.capture(frame="fake-frame")
    session.capture(frame="fake-frame")

    with pytest.raises(InconsistentPhotos):
        session.finalize()

    # A rejected alta must not leave a partial session behind either.
    assert session.is_complete is False


def test_finalize_accepts_consistent_photos():
    detector = FakeDetector([_detection()])
    base = np.array([1.0, 0.01, 0.0, 0.0], dtype=np.float32)

    class SequentialEmbedder(object):
        def __init__(self, vectors):
            self._vectors = list(vectors)

        def embed_from_landmarks(self, frame, landmarks):
            return self._vectors.pop(0)

    vectors = [base, base, base]
    session = EnrollmentSession(detector, SequentialEmbedder(vectors), config=RecognitionConfig())
    session.capture(frame="fake-frame")
    session.capture(frame="fake-frame")
    session.capture(frame="fake-frame")

    captures = session.finalize()
    assert len(captures) == 3
