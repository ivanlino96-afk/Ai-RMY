from fastapi.testclient import TestClient

from app.backend.dependencies import get_pipeline
from app.backend.main import app
from vision.pipeline import SharedState


class _FakeEventsPipeline(object):
    def __init__(self):
        self.state = SharedState()


def test_websocket_forwards_multi_detection_event_with_camera_state():
    """T18: the WS payload is a list of detections (one recognized, one not)
    plus the camera-connection field from T12 -- not the old singular
    'detection' shape."""
    fake_pipeline = _FakeEventsPipeline()
    app.dependency_overrides[get_pipeline] = lambda: fake_pipeline
    try:
        client = TestClient(app)
        with client.websocket_connect("/api/ws/events") as websocket:
            fake_pipeline.state.publish(
                b"jpeg-bytes",
                {
                    "frame_width": 640,
                    "frame_height": 480,
                    "detections": [
                        {"bbox": [0, 0, 10, 10], "score": 0.95, "label": "Ada"},
                        {"bbox": [50, 50, 10, 10], "score": 0.4, "label": "Desconocido"},
                    ],
                    "telemetry": None,
                    "serial_connected": False,
                    "tracking_enabled": True,
                    "camera_connected": True,
                },
            )
            event = websocket.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert len(event["detections"]) == 2
    assert event["detections"][0]["label"] == "Ada"
    assert event["detections"][1]["label"] == "Desconocido"
    assert event["camera_connected"] is True
