import json
from unittest.mock import Mock

import pytest

from vision.pipeline import Pipeline
from vision.serial_link.protocol import Telemetry, encode_move_steps, parse_telemetry


@pytest.mark.parametrize('pan,tilt', [(2001, 0), (-2001, 0), (1, 1), (0, 0), (1.5, 0), (True, 0)])
def test_invalid_steps(pan, tilt):
    with pytest.raises(ValueError):
        encode_move_steps(pan, tilt, 1)


def test_steps_roundtrip():
    assert json.loads(encode_move_steps(0, -2000, 8)) == {
        'proto': 1, 'cmd': 'move_steps', 'pan_steps': 0, 'tilt_steps': -2000, 'seq': 8}
    t = parse_telemetry('{"proto":1,"ok":true,"seq":8,"pan_deg":0,"tilt_deg":0,"moving":false,"homed":true,"calibration":true,"pan_steps":100,"tilt_steps":-2000}')
    assert t.calibration and t.pan_steps == 100 and t.tilt_steps == -2000


@pytest.mark.parametrize('blocked', ['tracking', 'scan', 'defense', 'offline', 'moving', 'normal', 'missing', None])
def test_pipeline_calibration_gates(blocked):
    from vision.motor_settings import MotorSettings, StepLimits
    p = Pipeline.__new__(Pipeline)
    p.motor_settings = MotorSettings()
    p.step_limits = StepLimits()
    p._tracking_enabled = blocked == 'tracking'
    p._scan_active = blocked == 'scan'
    p._defense_active = blocked == 'defense'
    p._serial_link = Mock()
    p._serial_link.connected = blocked != 'offline'
    p._serial_link.last_telemetry = None if blocked == 'missing' else Telemetry(
        True, 1, 0, 0, blocked == 'moving', True, None, blocked != 'normal', 0, 0)
    p._serial_link.send_move_steps.return_value = True
    assert p.jog_steps(20, 0) == (blocked in (None, "normal"))
    assert p._serial_link.send_move_steps.called == (blocked in (None, "normal"))


@pytest.mark.parametrize('pan,tilt,dp,dt,accepted', [(12000,0,1,0,False),(0,0,-1,0,False),(0,1500,0,1,False),(0,-1500,0,-1,False),(11900,0,100,0,True)])
def test_step_boundaries(pan, tilt, dp, dt, accepted):
    from vision.motor_settings import MotorSettings, StepLimits
    p = Pipeline.__new__(Pipeline)
    p.motor_settings, p.step_limits = MotorSettings(), StepLimits()
    p._tracking_enabled = p._scan_active = p._defense_active = False
    p._serial_link = Mock()
    p._serial_link.connected = True
    p._serial_link.last_telemetry = Telemetry(True, 1, 0, 0, False, True, None, True, pan, tilt)
    p._serial_link.send_move_steps.return_value = True
    assert p.jog_steps(dp, dt) == accepted
    assert p._serial_link.send_move_steps.called == accepted
