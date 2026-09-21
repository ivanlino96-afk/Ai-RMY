import numpy as np
import pytest

from vision.config import PipelineConfig
from vision.detection.yunet import Detection
from vision.pipeline import UNKNOWN_LABEL, Pipeline, SharedState, _IdentityMemory
from vision.storage.repository import FaceRepository
from vision.tracking.controller import PixelOffset, TrackingController

_LANDMARKS = ((0.0, 0.0), (10.0, 0.0), (5.0, 5.0), (0.0, 10.0), (10.0, 10.0))


def _detection(x=0.0, y=0.0, w=20.0, h=20.0, score=0.99):
    return Detection(bbox=(x, y, w, h), landmarks=_LANDMARKS, score=score)


class FakeCv2(object):
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self):
        self.rectangles = []
        self.texts = []

    def line(self, *args, **kwargs):
        pass

    def rectangle(self, img, pt1, pt2, color, thickness):
        self.rectangles.append({"pt1": pt1, "pt2": pt2, "color": color})

    def putText(self, img, text, org, fontFace, fontScale, color, thickness):
        self.texts.append({"text": text, "color": color})

    def imencode(self, ext, img):
        return True, np.frombuffer(b"jpeg-bytes", dtype=np.uint8)


class FakeDetector(object):
    def __init__(self, detections):
        self._detections = detections

    def detect(self, frame):
        return self._detections


class FakeEmbedder(object):
    def __init__(self, vector=None):
        self._vector = np.ones(4, dtype=np.float32) if vector is None else np.asarray(vector, dtype=np.float32)

    def embed_from_landmarks(self, frame, landmarks):
        return self._vector


def _frame():
    return np.zeros((100, 100, 3), dtype=np.uint8)


def _pipeline(tmp_path, detections=None, embedder=None, repository=None):
    config = PipelineConfig()
    config = config._replace(
        storage=config.storage._replace(
            db_path=str(tmp_path / "faces.db"), photos_dir=str(tmp_path / "photos")
        )
    )
    repo = repository if repository is not None else FaceRepository(config.storage)
    pipeline = Pipeline(config=config, repository=repo)
    pipeline._detector = FakeDetector(detections if detections is not None else [_detection()])
    pipeline._embedder = embedder if embedder is not None else FakeEmbedder()
    return pipeline


# -- T9: multi-face detection, no registered people -> all "Desconocido" ----


def test_process_frame_reports_all_unmatched_faces_as_desconocido(tmp_path):
    detections = [_detection(x=0), _detection(x=50), _detection(x=100)]
    pipeline = _pipeline(tmp_path, detections=detections)

    pipeline._frame_count = pipeline._config.recognition.run_every_n_frames - 1
    pipeline._process_frame(FakeCv2(), _frame())

    event = pipeline.state.latest_event()
    assert len(event["detections"]) == 3
    assert all(d["label"] == UNKNOWN_LABEL for d in event["detections"])


# -- tracking_offset: same numbers the event carries as go to the motors ----


def test_event_tracking_offset_matches_controller_for_off_center_face(tmp_path):
    detection = _detection(x=0, y=0, w=20, h=20)  # center (10, 10) on a 100x100 frame
    pipeline = _pipeline(tmp_path, detections=[detection])

    pipeline._process_frame(FakeCv2(), _frame())

    event = pipeline.state.latest_event()
    offset = PixelOffset(dx=-40.0, dy=-40.0, frame_width=100, frame_height=100)
    expected = TrackingController().compute(offset)

    assert event["tracking_offset"] == {
        "dx": offset.dx,
        "dy": offset.dy,
        "pan_deg": expected.pan_deg,
        "tilt_deg": expected.tilt_deg,
        "centered": False,
    }


def test_event_tracking_offset_reports_centered_within_deadband(tmp_path):
    detection = _detection(x=40, y=40, w=20, h=20)  # center (50, 50): frame's exact center
    pipeline = _pipeline(tmp_path, detections=[detection])

    pipeline._process_frame(FakeCv2(), _frame())

    event = pipeline.state.latest_event()
    assert event["tracking_offset"] == {
        "dx": 0.0,
        "dy": 0.0,
        "pan_deg": 0.0,
        "tilt_deg": 0.0,
        "centered": True,
    }


def test_event_tracking_offset_is_none_without_a_target(tmp_path):
    pipeline = _pipeline(tmp_path, detections=[])

    pipeline._process_frame(FakeCv2(), _frame())

    event = pipeline.state.latest_event()
    assert event["tracking_offset"] is None


# -- T10: identity memory keeps identity within window, forgets past it -----


def test_identity_memory_keeps_identity_within_window_seconds():
    clock = {"now": 0.0}
    memory = _IdentityMemory(window_seconds=30.0, time_fn=lambda: clock["now"])

    memory.remember(center=(50.0, 50.0), label="Ada", now=0.0)

    clock["now"] = 10.0
    label, found = memory.recall(center=(52.0, 51.0), now=10.0)
    assert found is True
    assert label == "Ada"


def test_identity_memory_forgets_identity_past_window_seconds():
    memory = _IdentityMemory(window_seconds=30.0)

    memory.remember(center=(50.0, 50.0), label="Ada", now=0.0)

    label, found = memory.recall(center=(52.0, 51.0), now=40.0)
    assert found is False
    assert label is None


# -- T11: annotation draws the shared centre reticle, nothing per-face ------
# (RF-12/RF-13's green/red box + label is rendered once, client-side, by
# DetectionOverlay -- this layer only encodes the raw frame for the MJPEG
# stream, so it must not draw its own per-face box/text on top of it.)


def test_annotate_draws_no_per_face_box_or_label(tmp_path):
    pipeline = _pipeline(tmp_path)
    cv2 = FakeCv2()

    pipeline._annotate(cv2, _frame())

    assert cv2.rectangles == []
    assert cv2.texts == []


# -- T12: camera connect/disconnect publishes once per transition -----------


def test_camera_transitions_publish_exactly_once_per_transition(tmp_path):
    pipeline = _pipeline(tmp_path, detections=[])
    cv2 = FakeCv2()

    publishes = []
    original_publish = pipeline.state.publish

    def counting_publish(jpeg, event):
        publishes.append(event)
        original_publish(jpeg, event)

    pipeline.state.publish = counting_publish

    frame_sequence = [_frame(), None, None, None, _frame(), _frame(), None, _frame()]
    for frame in frame_sequence:
        pipeline._handle_frame(cv2, frame)

    camera_states = [event["camera_connected"] for event in publishes]
    # One publish per valid frame, plus exactly one for each disconnect
    # transition -- not one per failed read while already disconnected.
    assert camera_states == [True, False, True, True, False, True]


def test_shared_state_wait_for_update_returns_on_publish():
    state = SharedState()
    state.publish(b"jpeg", {"foo": "bar"})
    event, version = state.wait_for_update(last_version=0, timeout=1.0)
    assert event == {"foo": "bar"}
    assert version == 1


# -- pipeline thread survives a single bad frame -----------------------------


class _RaisingDetector(object):
    def detect(self, frame):
        raise RuntimeError("simulated OpenCV DNN shape-mismatch crash")


class _FakeCamera(object):
    def __init__(self, frames):
        self._frames = list(frames)

    def read(self):
        return self._frames.pop(0)


def test_run_once_survives_a_single_bad_frame_and_keeps_processing(tmp_path):
    """A single frame that raises while processing (e.g. the OpenCV DNN
    shape-mismatch crash this regression-tests) must not kill the
    vision-pipeline thread -- otherwise the MJPEG/WS endpoints keep
    serving a frozen last frame forever with no recovery."""
    pipeline = _pipeline(tmp_path, detections=[_detection()])
    good_detector = pipeline._detector
    pipeline._detector = _RaisingDetector()
    pipeline._camera = _FakeCamera([_frame(), _frame()])

    pipeline._run_once(FakeCv2())  # bad frame: must not raise
    assert pipeline.state.latest_event() is None

    pipeline._detector = good_detector
    pipeline._run_once(FakeCv2())  # next frame: pipeline recovered
    event = pipeline.state.latest_event()
    assert event is not None
    assert len(event["detections"]) == 1
