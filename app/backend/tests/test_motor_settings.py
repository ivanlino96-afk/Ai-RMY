from vision.motor_settings import MotorSettings


def test_profiles_api(client, fake_pipeline, tmp_path):
    fake_pipeline.motor_settings = MotorSettings(str(tmp_path / 'motor-speeds.json'))
    before = client.get('/api/settings/motor-speeds').json()
    response = client.post('/api/settings/motor-speeds/automatic', json={'pan': 120, 'tilt': 80, 'pan_acceleration': 200, 'tilt_acceleration': 150})
    assert response.status_code == 200
    assert response.json()['automatic'] == {'pan': 120, 'tilt': 80, 'pan_acceleration': 200, 'tilt_acceleration': 150}
    assert response.json()['manual'] == before['manual']
    assert client.get('/api/settings/motor-speeds').json() == response.json()


def test_settings_api_rejects_invalid_values(client, fake_pipeline):
    fake_pipeline.motor_settings = MotorSettings()
    for value in (0, 4001, 10.5, True, '160'):
        assert client.post('/api/settings/motor-speeds/manual', json={'pan': value, 'tilt': 80, 'pan_acceleration': 400, 'tilt_acceleration': 400}).status_code == 422
    assert client.post('/api/settings/motor-speeds/wrong', json={'pan': 100, 'tilt': 80, 'pan_acceleration': 400, 'tilt_acceleration': 400}).status_code == 400
    assert client.post('/api/settings/motor-speeds/manual', json={'pan': 100}).status_code == 422


def test_acceleration_api(client, fake_pipeline):
    fake_pipeline.motor_settings = MotorSettings()
    payload = {'pan': 4000, 'tilt': 2000, 'pan_acceleration': 20000, 'tilt_acceleration': 1000}
    assert client.post('/api/settings/motor-speeds/manual', json=payload).status_code == 200
    for invalid in (0, -1, 20001, True, '400'):
        payload['pan_acceleration'] = invalid
        assert client.post('/api/settings/motor-speeds/manual', json=payload).status_code == 422


def test_step_limits_api(client, fake_pipeline, tmp_path):
    from vision.motor_settings import StepLimits
    path = str(tmp_path / 'step-limits.json')
    fake_pipeline.step_limits = StepLimits(path)
    limits = client.get('/api/settings/step-limits').json()
    assert limits == dict(pan_min=0, pan_max=12000, tilt_min=-1500, tilt_max=1500)
    limits['pan_max'] = 10000
    assert client.post('/api/settings/step-limits', json=limits).status_code == 200
    assert StepLimits(path).get('limits') == limits
    for invalid in (True, '12000', 1.5, -1, 200001):
        assert client.post('/api/settings/step-limits', json=dict(limits, pan_max=invalid)).status_code == 422
