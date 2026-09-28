"""Shared TestClient fixtures for backend integration tests.

The FastAPI app's lifespan (app/backend/main.py) builds a real vision
Pipeline/FaceRepository from default config paths -- fine in production, but
tests never trigger it (no `with TestClient(...)`) and instead override
get_repository/get_pipeline/get_enrollment_sessions directly, so nothing
touches vision/data/ or requires cv2/onnxruntime.
"""

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.backend.dependencies import get_enrollment_sessions, get_pipeline, get_repository
from app.backend.main import app
from vision.config import PipelineConfig, StorageConfig
from vision.detection.yunet import Detection
from vision.storage.repository import FaceRepository

_LANDMARKS = ((0.0, 0.0), (10.0, 0.0), (5.0, 5.0), (0.0, 10.0), (10.0, 10.0))


class FakeDetector(object):
    """Always reports exactly one face -- enrollment photos require exactly
    one; multi-face rejection is covered at the vision layer (test_enroll.py)."""

    def detect(self, frame):
        return [Detection(bbox=(0.0, 0.0, 20.0, 20.0), landmarks=_LANDMARKS, score=0.99)]


class FakeEmbedder(object):
    """Same vector for every photo by default, so the 3-photo consistency
    check (RF-5) passes -- tests needing an outlier swap this out."""

    def __init__(self, vector=None):
        self._vector = (
            np.ones(4, dtype=np.float32) if vector is None else np.asarray(vector, dtype=np.float32)
        )

    def embed_from_landmarks(self, frame, landmarks):
        return self._vector


class FakeState(object):
    """Stands in for Pipeline.SharedState -- video.py only ever reads
    latest_jpeg() from it."""

    def __init__(self, jpeg=b"fake-jpeg-bytes"):
        self._jpeg = jpeg

    def latest_jpeg(self):
        return self._jpeg


class FakePipeline(object):
    def __init__(self, config, detector=None, embedder=None):
        self.detector = detector or FakeDetector()
        self.embedder = embedder or FakeEmbedder()
        self.config = config
        self.state = FakeState()
        self.last_telemetry = None
        self.serial_connected = False
        self.tracking_enabled = True
        self.last_jog = None
        self.stopped = False
        self.camera_index = None
        self._camera_list = [
            {"index": 0, "width": 640, "height": 480},
            {"index": 1, "width": 1920, "height": 1080},
        ]
        self._scan_state = "idle"
        self._scan_progress = 0.0
        self._scan_results = []
        self.scan_started_with = None
        self.scan_cancelled = False
        self._defense_active = False
        self._defense_armed_at = None
        self._defense_log = []

    def center(self):
        pass

    def set_tracking_enabled(self, enabled):
        if enabled and self._scan_state == "running":
            return False
        if not enabled and self._defense_active:
            return False
        self.tracking_enabled = enabled
        return True

    def jog(self, pan_deg=0.0, tilt_deg=0.0):
        self.last_jog = (pan_deg, tilt_deg)
        return not self.tracking_enabled

    def emergency_stop(self):
        self.stopped = True
        self.cancel_scan()
        self.stop_defense_mode()

    def list_cameras(self):
        return self._camera_list

    def select_camera(self, device_index):
        self.camera_index = device_index

    def start_scan(self, pan_range_deg=None, tilt_range_deg=None, step_deg=None):
        if self.tracking_enabled or self._scan_state == "running":
            return False
        self.scan_started_with = (pan_range_deg, tilt_range_deg, step_deg)
        self._scan_state = "running"
        self._scan_progress = 0.0
        return True

    def cancel_scan(self):
        self.scan_cancelled = True
        self._scan_state = "idle"
        self._scan_progress = 0.0

    def scan_status(self):
        return {
            "state": self._scan_state,
            "progress": self._scan_progress,
            "results": self._scan_results,
        }

    def start_defense_mode(self):
        if self._defense_active or self._scan_state == "running":
            return False
        self._defense_active = True
        self._defense_armed_at = time.time()
        return True

    def stop_defense_mode(self):
        self._defense_active = False
        self._defense_armed_at = None

    def defense_status(self):
        return {
            "active": self._defense_active,
            "armed_at": self._defense_armed_at,
            "log": self._defense_log,
        }


@pytest.fixture
def repository(tmp_path):
    config = StorageConfig(
        db_path=str(tmp_path / "faces.db"), photos_dir=str(tmp_path / "photos")
    )
    repo = FaceRepository(config)
    yield repo
    repo.close()


@pytest.fixture
def fake_pipeline():
    return FakePipeline(PipelineConfig())


@pytest.fixture
def client(repository, fake_pipeline, monkeypatch):
    sessions = {}
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_pipeline] = lambda: fake_pipeline
    app.dependency_overrides[get_enrollment_sessions] = lambda: sessions

    # decode_image() lazily imports cv2, unavailable on this dev machine.
    # FakeDetector doesn't inspect frame content, so any placeholder is fine.
    monkeypatch.setattr(
        "app.backend.routers.people.decode_image", lambda image_bytes: image_bytes
    )

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
