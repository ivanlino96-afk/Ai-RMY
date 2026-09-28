def test_defense_arm_succeeds_and_reports_ok(client, fake_pipeline):
    response = client.post("/api/defense/arm")

    assert response.json() == {"ok": True}
    assert fake_pipeline._defense_active is True


def test_defense_arm_refused_while_scan_running(client, fake_pipeline):
    fake_pipeline._scan_state = "running"

    response = client.post("/api/defense/arm")

    assert response.json() == {"ok": False}
    assert fake_pipeline._defense_active is False


def test_defense_disarm_always_reports_ok(client, fake_pipeline):
    client.post("/api/defense/arm")

    response = client.post("/api/defense/disarm")

    assert response.json() == {"ok": True}
    assert fake_pipeline._defense_active is False


def test_defense_status_reports_pipeline_snapshot(client, fake_pipeline):
    fake_pipeline._defense_active = True
    fake_pipeline._defense_armed_at = 123.0
    fake_pipeline._defense_log = [
        {"type": "identified", "timestamp": 124.0, "name": "Alice", "photo": None},
        {"type": "threat", "timestamp": 128.0, "name": None, "photo": "128_abcd1234.jpg"},
    ]

    response = client.get("/api/defense/status")

    assert response.json() == {
        "active": True,
        "armed_at": 123.0,
        "log": [
            {"type": "identified", "timestamp": 124.0, "name": "Alice", "photo": None},
            {"type": "threat", "timestamp": 128.0, "name": None, "photo": "128_abcd1234.jpg"},
        ],
    }


def test_defense_photo_returns_404_when_missing(client, fake_pipeline):
    response = client.get("/api/defense/photo/nonexistent.jpg")

    assert response.status_code == 404


def test_defense_photo_returns_400_for_path_traversal(fake_pipeline):
    # FastAPI's route converter for a plain {filename} segment can't contain
    # "/", so an HTTP-level traversal attempt never reaches the handler --
    # call it directly to exercise the os.path.basename guard itself.
    from fastapi import HTTPException

    from app.backend.routers.defense import defense_photo

    try:
        defense_photo("../etc/passwd", pipeline=fake_pipeline)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_defense_photo_returns_200_when_file_exists(client, fake_pipeline, tmp_path):
    fake_pipeline.config = fake_pipeline.config._replace(
        storage=fake_pipeline.config.storage._replace(alarms_dir=str(tmp_path))
    )
    photo_path = tmp_path / "123_deadbeef.jpg"
    photo_path.write_bytes(b"fake-jpeg-bytes")

    response = client.get("/api/defense/photo/123_deadbeef.jpg")

    assert response.status_code == 200
    assert response.content == b"fake-jpeg-bytes"
