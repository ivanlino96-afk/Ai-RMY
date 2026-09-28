def test_camera_list_returns_detected_devices(client, fake_pipeline):
    response = client.get("/api/camera/list")

    assert response.json() == {
        "cameras": [
            {"index": 0, "width": 640, "height": 480},
            {"index": 1, "width": 1920, "height": 1080},
        ]
    }


def test_camera_select_sets_the_requested_device(client, fake_pipeline):
    response = client.post("/api/camera/select", json={"device_index": 1})

    assert response.json() == {"ok": True, "device_index": 1}
    assert fake_pipeline.camera_index == 1


def test_camera_select_with_null_device_index_releases_the_camera(client, fake_pipeline):
    fake_pipeline.camera_index = 1

    response = client.post("/api/camera/select", json={"device_index": None})

    assert response.json() == {"ok": True, "device_index": None}
    assert fake_pipeline.camera_index is None
