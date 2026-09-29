import json
from unittest.mock import Mock

import pytest

from vision.motor_settings import MotorSettings, StepLimits
from vision.pipeline import Pipeline
from vision.serial_link.protocol import encode_move_delta, encode_move_steps, encode_goto


def test_profiles_persist_independently(tmp_path):
    path = str(tmp_path / 'motor-speeds.json')
    settings = MotorSettings(path)
    settings.set('manual', {'pan': 200, 'tilt': 120, 'pan_acceleration': 400, 'tilt_acceleration': 300})
    settings.set('automatic', {'pan': 75, 'tilt': 50, 'pan_acceleration': 100, 'tilt_acceleration': 80})
    restored = MotorSettings(path)
    assert restored.all() == {'manual': {'pan': 200, 'tilt': 120, 'pan_acceleration': 400, 'tilt_acceleration': 300}, 'automatic': {'pan': 75, 'tilt': 50, 'pan_acceleration': 100, 'tilt_acceleration': 80}}
    snapshot = restored.get('manual')
    snapshot['pan'] = 999
    assert restored.get('manual')['pan'] == 200


@pytest.mark.parametrize('value', [0, -1, 4001, 1.5, True, '80', float('nan')])
def test_invalid_settings_do_not_change_profile(value):
    settings = MotorSettings()
    before = settings.all()
    with pytest.raises(ValueError):
        settings.set('manual', {'pan': value, 'tilt': 80, 'pan_acceleration': 400, 'tilt_acceleration': 400})
    assert settings.all() == before


def test_corrupt_settings_use_defaults(tmp_path):
    path = tmp_path / 'motor-speeds.json'
    path.write_text('{bad')
    assert MotorSettings(str(path)).get('manual') == {'pan': 160, 'tilt': 160, 'pan_acceleration': 400, 'tilt_acceleration': 400}


@pytest.mark.parametrize('encoder,args', [(encode_move_delta, (1, 0, 4)), (encode_move_steps, (20, 0, 4)), (encode_goto, (0, 0, 4))])
def test_motion_encodes_speeds_and_validates(encoder, args):
    result = json.loads(encoder(*args, speeds={'pan': 160, 'tilt': 100}))
    assert result['pan_speed'] == 160 and result['tilt_speed'] == 100
    with pytest.raises(ValueError):
        encoder(*args, speeds={'pan': 4001, 'tilt': 100})


def test_manual_jog_uses_manual_profile():
    pipeline = Pipeline.__new__(Pipeline)
    pipeline._tracking_enabled = False
    pipeline.motor_settings = MotorSettings()
    pipeline.step_limits = StepLimits()
    pipeline._serial_link = Mock()
    pipeline.jog(1, 0)
    pipeline._serial_link.send_move_delta.assert_called_once_with(1, 0, speeds=dict(pipeline.motor_settings.get('manual'), **pipeline.step_limits.get('limits')))


def test_migrate_old_file_keeps_speeds(tmp_path):
    path = tmp_path / 'motor-speeds.json'
    path.write_text(json.dumps({'manual': {'pan': 400, 'tilt': 350}, 'automatic': {'pan': 120, 'tilt': 80}}))
    settings = MotorSettings(str(path))
    assert settings.get('manual') == {'pan': 400, 'tilt': 350, 'pan_acceleration': 400, 'tilt_acceleration': 400}
    assert settings.get('automatic')['pan_acceleration'] == 40


@pytest.mark.parametrize('value', [0, 20001, 0.5, True, float('inf')])
def test_acceleration_validation(value):
    settings = MotorSettings()
    payload = settings.get('manual')
    payload['pan_acceleration'] = value
    with pytest.raises(ValueError):
        settings.set('manual', payload)
    with pytest.raises(ValueError):
        encode_move_steps(20, 0, 3, payload)


def test_full_motion_profile_encodes_at_upper_bound():
    payload = {'pan': 4000, 'tilt': 1000, 'pan_acceleration': 20000, 'tilt_acceleration': 1000}
    result = json.loads(encode_move_steps(2000, 0, 5, payload))
    assert result['pan_accel'] == 20000
    assert result['tilt_accel'] == 1000
    assert result['pan_speed'] == 4000
