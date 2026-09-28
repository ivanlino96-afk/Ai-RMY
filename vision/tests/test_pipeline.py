import numpy as np
import pytest

from vision.config import PipelineConfig
from vision.detection.yunet import Detection
from vision.pipeline import (
    _CAMERA_WARMUP_MAX_FAILED_READS,
    UNKNOWN_LABEL,
    Pipeline,
    SharedState,
    _IdentityMemory,
)
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
            db_path=str(tmp_path / "faces.db"),
            photos_dir=str(tmp_path / "photos"),
            alarms_dir=str(tmp_path / "alarms"),
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


# -- manual mode: Pipeline.jog() gates on tracking being disabled -----------


class FakeSerialLink(object):
    def __init__(self):
        self.moves = []
        self.gotos = []
        self.stops = 0
        self.last_telemetry = None
        self.connected = True

    def send_move_delta(self, pan_deg, tilt_deg):
        self.moves.append((pan_deg, tilt_deg))

    def send_goto(self, pan_deg, tilt_deg):
        self.gotos.append((pan_deg, tilt_deg))

    def send_stop(self):
        self.stops += 1


def test_jog_sends_move_delta_when_tracking_disabled(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.set_tracking_enabled(False)

    sent = pipeline.jog(pan_deg=10.0, tilt_deg=-5.0)

    assert sent is True
    assert pipeline._serial_link.moves == [(10.0, -5.0)]


def test_jog_refuses_when_tracking_enabled(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()

    sent = pipeline.jog(pan_deg=10.0, tilt_deg=0.0)

    assert sent is False
    assert pipeline._serial_link.moves == []


def test_emergency_stop_forwards_to_serial_link(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()

    pipeline.emergency_stop()

    assert pipeline._serial_link.stops == 1


# -- room scan: state machine gating + _service_scan's step-through --------


class _FakeTelemetry(object):
    def __init__(self, moving):
        self.moving = moving


def test_start_scan_refuses_while_tracking_enabled(tmp_path):
    pipeline = _pipeline(tmp_path)  # tracking_enabled defaults to True

    assert pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)) is False
    assert pipeline.scan_status()["state"] == "idle"


def test_start_scan_refuses_while_a_scan_is_already_active(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.set_tracking_enabled(False)

    assert pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)) is True
    assert pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)) is False


def test_set_tracking_enabled_refuses_while_scan_active(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.set_tracking_enabled(False)
    pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0))

    assert pipeline.set_tracking_enabled(True) is False
    assert pipeline.tracking_enabled is False


def test_emergency_stop_cancels_an_active_scan(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.set_tracking_enabled(False)
    pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0))

    pipeline.emergency_stop()

    assert pipeline.scan_status()["state"] == "idle"
    # set_tracking_enabled(False)'s send_stop(), emergency_stop()'s own
    # send_stop(), and cancel_scan()'s send_stop() since the scan was
    # active -- all three must fire.
    assert pipeline._serial_link.stops == 3


def test_process_frame_does_not_send_move_delta_while_scan_active(tmp_path):
    detection = _detection(x=0, y=0, w=20, h=20)  # off-center -> would normally move
    pipeline = _pipeline(tmp_path, detections=[detection])
    pipeline._serial_link = FakeSerialLink()
    pipeline._scan_active = True  # simulate a scan owning the gimbal

    pipeline._process_frame(FakeCv2(), _frame())

    assert pipeline._serial_link.moves == []
    # The UI still gets the computed offset -- only the motor command is gated.
    assert pipeline.state.latest_event()["tracking_offset"] is not None


class FakeObjectDetector(object):
    def __init__(self, detections):
        self._detections = detections

    def detect(self, frame):
        return self._detections


def test_service_scan_steps_through_goto_arrival_dwell_and_detect(tmp_path):
    from vision.detection.objects import ObjectDetection

    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline._object_detector = FakeObjectDetector(
        [ObjectDetection(bbox=(1.0, 2.0, 3.0, 4.0), label="chair", score=0.8)]
    )
    pipeline.set_tracking_enabled(False)
    assert pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)) is True

    clock = {"t": 0.0}
    with_clock = pytest.MonkeyPatch()
    with_clock.setattr("vision.pipeline.time.monotonic", lambda: clock["t"])
    try:
        cv2 = FakeCv2()
        frame = _frame()

        # First tick: sends the waypoint's goto, nothing else yet.
        pipeline._service_scan(cv2, frame)
        assert pipeline._serial_link.gotos == [(0.0, 0.0)]
        assert pipeline.scan_status()["state"] == "running"

        # Still moving -- keeps waiting, no dwell timer started yet.
        pipeline._serial_link.last_telemetry = _FakeTelemetry(moving=True)
        pipeline._service_scan(cv2, frame)
        assert pipeline.scan_status()["results"] == []

        # Arrival: starts the dwell timer, doesn't detect yet.
        pipeline._serial_link.last_telemetry = _FakeTelemetry(moving=False)
        pipeline._service_scan(cv2, frame)
        assert pipeline.scan_status()["results"] == []

        # Dwell not yet elapsed -- still waiting.
        clock["t"] += 1.0
        pipeline._service_scan(cv2, frame)
        assert pipeline.scan_status()["results"] == []

        # Dwell elapsed -- detects, records the result, and (single waypoint)
        # finishes the scan.
        clock["t"] += 1.0
        pipeline._service_scan(cv2, frame)
    finally:
        with_clock.undo()

    status = pipeline.scan_status()
    assert status["state"] == "done"
    assert status["progress"] == 1.0
    assert status["results"] == [
        {
            "pan_deg": 0.0,
            "tilt_deg": 0.0,
            "objects": [{"bbox": [1.0, 2.0, 3.0, 4.0], "label": "chair", "score": 0.8}],
        }
    ]


def test_service_scan_arrives_via_timeout_when_telemetry_never_reports_stopped(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline._object_detector = FakeObjectDetector([])
    pipeline.set_tracking_enabled(False)
    pipeline.start_scan(
        pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)
    )
    arrival_timeout_s = pipeline._scan_config.arrival_timeout_s
    dwell_s = pipeline._scan_config.dwell_s

    clock = {"t": 0.0}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("vision.pipeline.time.monotonic", lambda: clock["t"])
    try:
        cv2 = FakeCv2()
        frame = _frame()

        pipeline._service_scan(cv2, frame)  # sends goto
        pipeline._serial_link.last_telemetry = _FakeTelemetry(moving=True)  # never stops

        clock["t"] += arrival_timeout_s
        pipeline._service_scan(cv2, frame)  # timed out -> treated as arrived
        clock["t"] += dwell_s
        pipeline._service_scan(cv2, frame)  # dwell elapsed -> detects + advances
    finally:
        monkeypatch.undo()

    assert pipeline.scan_status()["state"] == "done"


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


def test_run_once_with_no_camera_selected_reports_disconnected(tmp_path):
    """Before any select_camera() call (or after one that failed to open),
    self._camera is None -- this must behave exactly like a disconnected
    camera, not raise, so the worker thread keeps running and serving
    events forever until a selection succeeds."""
    pipeline = _pipeline(tmp_path)
    assert pipeline._camera is None

    pipeline._run_once(FakeCv2())

    event = pipeline.state.latest_event()
    assert event["camera_connected"] is False


# -- runtime camera selection: select_camera()/_sync_camera() -----------------


class _FakeCameraOK(object):
    def __init__(self, config):
        self.config = config
        self.released = False

    def read(self):
        return None

    def release(self):
        self.released = True


def test_select_camera_opens_the_requested_index(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(
        "vision.pipeline.Camera",
        lambda config: opened.append(config.device_index) or _FakeCameraOK(config),
    )
    pipeline = _pipeline(tmp_path)

    pipeline.select_camera(2)
    pipeline._sync_camera()

    assert opened == [2]
    assert pipeline.camera_index == 2
    assert pipeline._camera is not None


def test_sync_camera_is_a_noop_when_nothing_changed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "vision.pipeline.Camera", lambda config: calls.append(config.device_index) or _FakeCameraOK(config)
    )
    pipeline = _pipeline(tmp_path)
    pipeline.select_camera(0)
    pipeline._sync_camera()

    pipeline._sync_camera()  # same generation -- must not reopen

    assert calls == [0]


def test_select_camera_releases_the_previous_camera(tmp_path, monkeypatch):
    cameras = []
    monkeypatch.setattr(
        "vision.pipeline.Camera",
        lambda config: cameras.append(_FakeCameraOK(config)) or cameras[-1],
    )
    pipeline = _pipeline(tmp_path)

    pipeline.select_camera(0)
    pipeline._sync_camera()
    pipeline.select_camera(1)
    pipeline._sync_camera()

    assert cameras[0].released is True
    assert pipeline.camera_index == 1


def test_select_camera_failure_leaves_pipeline_without_a_camera(tmp_path, monkeypatch):
    def _raise(config):
        raise RuntimeError("could not open camera device index %d" % config.device_index)

    monkeypatch.setattr("vision.pipeline.Camera", _raise)
    pipeline = _pipeline(tmp_path)

    pipeline.select_camera(0)
    pipeline._sync_camera()  # must not raise

    assert pipeline._camera is None
    assert pipeline.camera_index is None

    pipeline._run_once(FakeCv2())  # loop keeps running, reports disconnected
    event = pipeline.state.latest_event()
    assert event["camera_connected"] is False


# -- self-healing: a camera that opens but never delivers a frame ----------
# Observed repeatedly on Windows: a freshly-opened VideoCapture reports
# isOpened() True immediately but every read() fails, sometimes forever,
# until the same index is released and reopened once in-process.


class _FakeCameraStuck(object):
    """Opens successfully but read() always fails -- until released."""

    def __init__(self, config):
        self.config = config
        self.released = False

    def read(self):
        return None

    def release(self):
        self.released = True


def test_stuck_camera_self_heals_after_grace_period(tmp_path, monkeypatch):
    monkeypatch.setattr("vision.pipeline.time.sleep", lambda seconds: None)
    cameras = []
    monkeypatch.setattr(
        "vision.pipeline.Camera",
        lambda config: cameras.append(_FakeCameraStuck(config)) or cameras[-1],
    )
    pipeline = _pipeline(tmp_path)
    pipeline.select_camera(0)
    pipeline._sync_camera()
    first_camera = pipeline._camera

    for _ in range(_CAMERA_WARMUP_MAX_FAILED_READS - 1):
        pipeline._run_once(FakeCv2())
        assert pipeline._camera is first_camera
        assert first_camera.released is False

    pipeline._run_once(FakeCv2())  # threshold reached -- forces a reopen

    assert first_camera.released is True
    assert len(cameras) == 2
    assert pipeline._camera is cameras[1]
    assert pipeline.camera_index == 0


def test_successful_frame_resets_the_stuck_camera_fail_count(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._camera = object()  # only needs to be not-None; never released here
    pipeline._camera_index = 0
    cv2 = FakeCv2()

    for _ in range(_CAMERA_WARMUP_MAX_FAILED_READS - 1):
        pipeline._handle_frame(cv2, None)
    assert pipeline._camera_fail_count == _CAMERA_WARMUP_MAX_FAILED_READS - 1

    pipeline._handle_frame(cv2, _frame())

    assert pipeline._camera_fail_count == 0


def test_failed_reopen_of_stuck_camera_leaves_pipeline_disconnected_cleanly(tmp_path, monkeypatch):
    def _raise(config):
        raise RuntimeError("could not reopen camera index %d" % config.device_index)

    monkeypatch.setattr("vision.pipeline.Camera", _raise)
    pipeline = _pipeline(tmp_path)
    pipeline._camera = _FakeCameraStuck(pipeline._config.camera)
    pipeline._camera_index = 0
    cv2 = FakeCv2()

    for _ in range(_CAMERA_WARMUP_MAX_FAILED_READS):
        pipeline._handle_frame(cv2, None)

    assert pipeline._camera is None
    assert pipeline.camera_index is None
    assert pipeline._camera_fail_count == 0

    pipeline._run_once(cv2)  # loop keeps running, still reports disconnected
    event = pipeline.state.latest_event()
    assert event["camera_connected"] is False


def test_list_cameras_delegates_to_capture_probe(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "vision.pipeline.list_available_cameras", lambda: [{"index": 0, "width": 640, "height": 480}]
    )
    pipeline = _pipeline(tmp_path)

    assert pipeline.list_cameras() == [{"index": 0, "width": 640, "height": 480}]


# -- defense mode / threat alarm ---------------------------------------------


def test_start_defense_mode_forces_tracking_on(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.set_tracking_enabled(False)

    assert pipeline.start_defense_mode() is True
    assert pipeline.tracking_enabled is True
    assert pipeline.defense_status()["active"] is True


def test_start_defense_mode_refuses_while_scan_active(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.set_tracking_enabled(False)
    assert pipeline.start_scan(pan_range_deg=(0.0, 0.0), tilt_range_deg=(0.0, 0.0)) is True

    assert pipeline.start_defense_mode() is False
    assert pipeline.defense_status()["active"] is False


def test_start_defense_mode_refuses_when_already_active(tmp_path):
    pipeline = _pipeline(tmp_path)

    assert pipeline.start_defense_mode() is True
    assert pipeline.start_defense_mode() is False


def test_stop_defense_mode_restores_previous_tracking_state(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.set_tracking_enabled(False)

    pipeline.start_defense_mode()
    assert pipeline.tracking_enabled is True

    pipeline.stop_defense_mode()

    assert pipeline.tracking_enabled is False
    assert pipeline.defense_status()["active"] is False


def test_set_tracking_enabled_refuses_to_disable_while_armed(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()

    assert pipeline.set_tracking_enabled(False) is False
    assert pipeline.tracking_enabled is True


def test_emergency_stop_disarms_defense_mode(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline._serial_link = FakeSerialLink()
    pipeline.start_defense_mode()

    pipeline.emergency_stop()

    assert pipeline.defense_status()["active"] is False
    assert pipeline.tracking_enabled is True


def test_select_target_prioritizes_unrecognized_face_while_armed(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    recognized = _detection(x=0, y=0)
    unrecognized = _detection(x=50, y=50)

    target = pipeline._select_target([(recognized, "Ada"), (unrecognized, None)])

    assert target is unrecognized


def test_select_target_falls_back_to_largest_when_armed_and_all_recognized(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    only = _detection(x=0, y=0)

    target = pipeline._select_target([(only, "Ada")])

    assert target is only


def test_select_target_falls_back_to_largest_when_not_armed(tmp_path):
    pipeline = _pipeline(tmp_path)
    largest = _detection(x=0, y=0)
    smaller = _detection(x=50, y=50)

    target = pipeline._select_target([(largest, "Ada"), (smaller, None)])

    assert target is largest


def test_service_defense_is_noop_when_not_armed(tmp_path):
    pipeline = _pipeline(tmp_path)
    detection = _detection(x=0, y=0)

    pipeline._service_defense(_frame(), [(detection, None)], now=0.0)
    pipeline._service_defense(_frame(), [(detection, None)], now=10.0)

    assert pipeline.defense_status() == {"active": False, "armed_at": None, "log": []}


def test_service_defense_fires_threat_alarm_once_after_threat_seconds(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()
    threat_seconds = pipeline._config.defense.threat_seconds

    pipeline._service_defense(frame, [(detection, None)], now=0.0)
    assert pipeline.defense_status()["log"] == []

    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds - 0.1)
    assert pipeline.defense_status()["log"] == []

    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds)
    log = pipeline.defense_status()["log"]
    assert len(log) == 1
    assert log[0]["type"] == "threat"
    assert log[0]["photo"] is not None


def test_service_defense_saves_alarm_photo_to_configured_dir(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()
    threat_seconds = pipeline._config.defense.threat_seconds

    pipeline._service_defense(frame, [(detection, None)], now=0.0)
    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds)

    photo = pipeline.defense_status()["log"][0]["photo"]
    saved_path = tmp_path / "alarms" / photo
    assert saved_path.is_file()


def test_service_defense_does_not_repeat_alarm_while_sighting_persists(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()
    threat_seconds = pipeline._config.defense.threat_seconds

    pipeline._service_defense(frame, [(detection, None)], now=0.0)
    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds)
    first_log = list(pipeline.defense_status()["log"])
    assert len(first_log) == 1

    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds + 2.0)
    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds + 5.0)

    assert pipeline.defense_status()["log"] == first_log


def test_service_defense_suppresses_photo_after_sighting_gap_within_cooldown(tmp_path):
    """A suspect who disappears past sighting_timeout_s (head turn, missed
    detection frame) but reappears in roughly the same spot before
    alarm_photo_cooldown_s elapses gets a fresh timer (re-armed sighting) but
    no second photo -- that's the whole point of the cooldown."""
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()
    threat_seconds = pipeline._config.defense.threat_seconds
    sighting_timeout_s = pipeline._config.defense.sighting_timeout_s

    pipeline._service_defense(frame, [(detection, None)], now=0.0)
    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds)
    assert len(pipeline.defense_status()["log"]) == 1

    # Disappears for longer than sighting_timeout_s -- the stale sighting is
    # pruned at the end of this tick (no detections claim it).
    gone_at = threat_seconds + sighting_timeout_s + 0.5
    pipeline._service_defense(frame, [], now=gone_at)

    # Reappears well within alarm_photo_cooldown_s (default 10 minutes): a
    # brand new sighting starts its own 3s timer, but the photo is
    # suppressed since the cooldown from the first photo hasn't elapsed.
    reappeared_at = gone_at + 0.1
    pipeline._service_defense(frame, [(detection, None)], now=reappeared_at)
    pipeline._service_defense(frame, [(detection, None)], now=reappeared_at + threat_seconds)

    log = pipeline.defense_status()["log"]
    assert len(log) == 1


def test_service_defense_rearms_photo_once_cooldown_expires(tmp_path):
    """Past alarm_photo_cooldown_s, a suspect still lingering (or one who
    left and came back) is treated as a fresh intrusion and gets a new
    photo."""
    pipeline = _pipeline(tmp_path)
    pipeline._config = pipeline._config._replace(
        defense=pipeline._config.defense._replace(alarm_photo_cooldown_s=5.0)
    )
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()
    threat_seconds = pipeline._config.defense.threat_seconds
    sighting_timeout_s = pipeline._config.defense.sighting_timeout_s
    cooldown_s = pipeline._config.defense.alarm_photo_cooldown_s

    pipeline._service_defense(frame, [(detection, None)], now=0.0)
    pipeline._service_defense(frame, [(detection, None)], now=threat_seconds)
    assert len(pipeline.defense_status()["log"]) == 1

    gone_at = threat_seconds + sighting_timeout_s + 0.5
    pipeline._service_defense(frame, [], now=gone_at)

    reappeared_at = threat_seconds + cooldown_s + 1.0
    pipeline._service_defense(frame, [(detection, None)], now=reappeared_at)
    pipeline._service_defense(frame, [(detection, None)], now=reappeared_at + threat_seconds)

    log = pipeline.defense_status()["log"]
    assert len(log) == 2
    assert all(entry["type"] == "threat" for entry in log)


def test_service_defense_logs_identified_once_per_sighting(tmp_path):
    pipeline = _pipeline(tmp_path)
    pipeline.start_defense_mode()
    detection = _detection(x=0, y=0)
    frame = _frame()

    pipeline._service_defense(frame, [(detection, "Ada")], now=0.0)
    pipeline._service_defense(frame, [(detection, "Ada")], now=0.5)
    pipeline._service_defense(frame, [(detection, "Ada")], now=1.0)

    log = pipeline.defense_status()["log"]
    assert len(log) == 1
    assert log[0]["type"] == "identified"
    assert log[0]["name"] == "Ada"
    assert log[0]["photo"] is None


def test_defense_event_payload_is_none_when_idle_and_no_log(tmp_path):
    pipeline = _pipeline(tmp_path)

    assert pipeline._defense_event_payload() is None


def test_defense_event_payload_present_once_armed(tmp_path):
    pipeline = _pipeline(tmp_path)

    pipeline.start_defense_mode()

    assert pipeline._defense_event_payload() is not None
