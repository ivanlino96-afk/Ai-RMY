def test_jog_sends_delta_when_tracking_disabled(client, fake_pipeline):
    fake_pipeline.tracking_enabled = False

    response = client.post("/api/gimbal/jog", json={"pan_deg": 10.0, "tilt_deg": -5.0})

    assert response.json() == {"ok": True}
    assert fake_pipeline.last_jog == (10.0, -5.0)


def test_jog_refused_when_tracking_enabled(client, fake_pipeline):
    fake_pipeline.tracking_enabled = True

    response = client.post("/api/gimbal/jog", json={"pan_deg": 10.0, "tilt_deg": 0.0})

    assert response.json() == {"ok": False}


def test_jog_defaults_to_zero_delta(client, fake_pipeline):
    fake_pipeline.tracking_enabled = False

    response = client.post("/api/gimbal/jog", json={})

    assert response.json() == {"ok": True}
    assert fake_pipeline.last_jog == (0.0, 0.0)


def test_stop_always_succeeds(client, fake_pipeline):
    response = client.post("/api/gimbal/stop")

    assert response.json() == {"ok": True}
    assert fake_pipeline.stopped is True


def test_disabling_tracking_refused_while_defense_armed(client, fake_pipeline):
    fake_pipeline._defense_active = True

    response = client.post("/api/tracking/mode", json={"enabled": False})

    assert response.json()["ok"] is False
    assert fake_pipeline.tracking_enabled is True


def test_emergency_stop_disarms_defense_mode(client, fake_pipeline):
    client.post("/api/defense/arm")
    assert fake_pipeline._defense_active is True

    response = client.post("/api/gimbal/stop")

    assert response.json() == {"ok": True}
    assert fake_pipeline._defense_active is False
