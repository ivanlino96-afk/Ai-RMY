from vision.serial_link.protocol import (
    encode_goto,
    encode_home,
    encode_move_delta,
    encode_ping,
    encode_stop,
    parse_telemetry,
)


def test_encode_move_delta_includes_proto_and_fields():
    line = encode_move_delta(pan=-1.2, tilt=0.4, seq=102)
    assert line.endswith("\n")
    assert '"proto":1' in line
    assert '"cmd":"move_delta"' in line
    assert '"pan":-1.2' in line
    assert '"tilt":0.4' in line
    assert '"seq":102' in line


def test_encode_goto_uses_pan_deg_tilt_deg_field_names():
    line = encode_goto(pan_deg=10.0, tilt_deg=-5.0, seq=1)
    assert '"pan_deg":10.0' in line
    assert '"tilt_deg":-5.0' in line


def test_encode_stop_home_ping_are_bare_commands():
    assert '"cmd":"stop"' in encode_stop()
    assert '"cmd":"home"' in encode_home()
    assert '"cmd":"ping"' in encode_ping()


def test_parse_telemetry_roundtrip():
    line = (
        '{"proto":1,"ok":true,"seq":102,"pan_deg":12.4,"tilt_deg":-3.1,'
        '"moving":true,"homed":false}'
    )
    telemetry = parse_telemetry(line)
    assert telemetry is not None
    assert telemetry.ok is True
    assert telemetry.seq == 102
    assert telemetry.pan_deg == 12.4
    assert telemetry.tilt_deg == -3.1
    assert telemetry.moving is True
    assert telemetry.homed is False
    assert telemetry.error is None


def test_parse_telemetry_includes_error_field():
    line = (
        '{"proto":1,"ok":false,"seq":5,"pan_deg":0.0,"tilt_deg":0.0,'
        '"moving":false,"homed":false,"error":"limit exceeded"}'
    )
    telemetry = parse_telemetry(line)
    assert telemetry.ok is False
    assert telemetry.error == "limit exceeded"


def test_parse_telemetry_rejects_wrong_proto_version():
    line = '{"proto":2,"ok":true,"seq":1,"pan_deg":0,"tilt_deg":0,"moving":false,"homed":false}'
    assert parse_telemetry(line) is None


def test_parse_telemetry_rejects_malformed_json():
    assert parse_telemetry("not json") is None


def test_parse_telemetry_rejects_missing_fields():
    assert parse_telemetry('{"proto":1,"ok":true}') is None


def test_parse_telemetry_ignores_blank_lines():
    assert parse_telemetry("") is None
    assert parse_telemetry("   \n") is None
