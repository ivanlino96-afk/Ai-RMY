def test_scan_start_forwards_range_and_step_to_pipeline(client, fake_pipeline):
    fake_pipeline.tracking_enabled = False

    response = client.post(
        "/api/scan/start",
        json={"pan_range_deg": [-30.0, 30.0], "tilt_range_deg": [-10.0, 10.0], "step_deg": 15.0},
    )

    assert response.json() == {"ok": True}
    assert fake_pipeline.scan_started_with == ([-30.0, 30.0], [-10.0, 10.0], 15.0)


def test_scan_start_refused_while_tracking_enabled(client, fake_pipeline):
    fake_pipeline.tracking_enabled = True

    response = client.post("/api/scan/start", json={})

    assert response.json() == {"ok": False}


def test_scan_cancel_stops_an_active_scan(client, fake_pipeline):
    fake_pipeline.tracking_enabled = False
    client.post("/api/scan/start", json={})

    response = client.post("/api/scan/cancel")

    assert response.json() == {"ok": True}
    assert fake_pipeline.scan_cancelled is True
    assert fake_pipeline.scan_status()["state"] == "idle"


def test_scan_status_reports_pipeline_snapshot(client, fake_pipeline):
    fake_pipeline._scan_state = "done"
    fake_pipeline._scan_progress = 1.0
    fake_pipeline._scan_results = [
        {"pan_deg": 0.0, "tilt_deg": 0.0, "objects": [{"bbox": [1.0, 2.0, 3.0, 4.0], "label": "chair", "score": 0.8}]}
    ]

    response = client.get("/api/scan/status")

    assert response.json() == {
        "state": "done",
        "progress": 1.0,
        "results": [
            {
                "pan_deg": 0.0,
                "tilt_deg": 0.0,
                "objects": [{"bbox": [1.0, 2.0, 3.0, 4.0], "label": "chair", "score": 0.8}],
            }
        ],
    }
