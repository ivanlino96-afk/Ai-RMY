"""NDJSON protocol encode/decode — mirrors docs/protocol.md exactly.

This is the Jetson-side counterpart to firmware/lib/SerialProtocol. Any
change to the wire format must be made in docs/protocol.md first, then
reflected here AND in the firmware.

Dependency-free (stdlib json only) so it's testable without pyserial.
"""

import json
from typing import NamedTuple, Optional

PROTO_VERSION = 1


class Telemetry(NamedTuple):
    ok: bool
    seq: int
    pan_deg: float
    tilt_deg: float
    moving: bool
    homed: bool
    error: Optional[str] = None
    calibration: bool = False
    pan_steps: int = 0
    tilt_steps: int = 0


def _encode(payload):
    payload = dict(payload)
    payload["proto"] = PROTO_VERSION
    return json.dumps(payload, separators=(",", ":")) + "\n"


def _with_speeds(payload, speeds):
    if speeds is not None:
        for axis in ("pan", "tilt"):
            value = speeds[axis]
            if type(value) is not int or not 1 <= value <= 4000:
                raise ValueError("speed must be integer 1..4000 pulses/s")
            payload[axis + "_speed"] = value
        if "pan_acceleration" in speeds or "tilt_acceleration" in speeds:
            for axis in ("pan", "tilt"):
                value = speeds.get(axis + "_acceleration")
                if type(value) is not int or not 1 <= value <= 20000:
                    raise ValueError("acceleration must be integer 1..20000 pulses/s²")
                payload[axis + "_accel"] = value
        if any(key in speeds for key in ("pan_min", "pan_max", "tilt_min", "tilt_max")):
            from vision.motor_settings import StepLimits
            limits = {key: speeds.get(key) for key in ("pan_min", "pan_max", "tilt_min", "tilt_max")}
            StepLimits._validate("limits", limits)
            payload.update(limits)
    return _encode(payload)


def encode_move_delta(pan, tilt, seq, speeds=None):
    return _with_speeds({"cmd": "move_delta", "pan": pan, "tilt": tilt, "seq": seq}, speeds)


def encode_move_steps(pan_steps, tilt_steps, seq, speeds=None):
    if (type(pan_steps) is not int or type(tilt_steps) is not int or
            abs(pan_steps) > 2000 or abs(tilt_steps) > 2000 or
            (pan_steps == 0) == (tilt_steps == 0)):
        raise ValueError("one axis, 1..2000 integer pulses")
    return _with_speeds({"cmd": "move_steps", "pan_steps": pan_steps,
                    "tilt_steps": tilt_steps, "seq": seq}, speeds)


def encode_goto(pan_deg, tilt_deg, seq, speeds=None):
    return _with_speeds(
        {"cmd": "goto", "pan_deg": pan_deg, "tilt_deg": tilt_deg, "seq": seq}, speeds
    )


def encode_stop(seq=0):
    return _encode({"cmd": "stop", "seq": seq})


def encode_home(seq=0):
    return _encode({"cmd": "home", "seq": seq})


def encode_ping(seq=0):
    return _encode({"cmd": "ping", "seq": seq})


def parse_telemetry(line):
    """Parse one line of Arduino MKR Zero->Jetson telemetry/ack JSON.

    Returns None if the line isn't valid JSON, is missing required fields,
    or doesn't match the protocol version this client speaks — callers
    should treat that as "drop this line", not raise.
    """
    line = line.strip()
    if not line:
        return None
    try:
        doc = json.loads(line)
    except ValueError:
        return None

    if not isinstance(doc, dict) or doc.get("proto") != PROTO_VERSION:
        return None

    try:
        return Telemetry(
            ok=bool(doc["ok"]),
            seq=int(doc["seq"]),
            pan_deg=float(doc["pan_deg"]),
            tilt_deg=float(doc["tilt_deg"]),
            moving=bool(doc["moving"]),
            homed=bool(doc["homed"]),
            error=doc.get("error"),
            calibration=bool(doc.get("calibration", False)),
            pan_steps=int(doc.get("pan_steps", 0)),
            tilt_steps=int(doc.get("tilt_steps", 0)),
        )
    except (KeyError, TypeError, ValueError):
        return None
