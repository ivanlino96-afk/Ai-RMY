"""Shared TestClient fixtures for backend integration tests.

The FastAPI app's lifespan (app/backend/main.py) builds a real vision
Pipeline/FaceRepository from default config paths -- fine in production, but
tests never trigger it (no `with TestClient(...)`) and instead override
get_repository/get_pipeline/get_enrollment_sessions directly, so nothing
touches vision/data/ or requires cv2/onnxruntime.
"""

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


class FakePipeline(object):
    def __init__(self, config, detector=None, embedder=None):
        self.detector = detector or FakeDetector()
        self.embedder = embedder or FakeEmbedder()
        self.config = config
        self.last_telemetry = None
        self.serial_connected = False
        self.tracking_enabled = True

    def center(self):
        pass

    def set_tracking_enabled(self, enabled):
        self.tracking_enabled = enabled


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
