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


def _encode(payload):
    payload = dict(payload)
    payload["proto"] = PROTO_VERSION
    return json.dumps(payload, separators=(",", ":")) + "\n"


def encode_move_delta(pan, tilt, seq):
    return _encode({"cmd": "move_delta", "pan": pan, "tilt": tilt, "seq": seq})


def encode_goto(pan_deg, tilt_deg, seq):
    return _encode(
        {"cmd": "goto", "pan_deg": pan_deg, "tilt_deg": tilt_deg, "seq": seq}
    )


def encode_stop(seq=0):
    return _encode({"cmd": "stop", "seq": seq})


def encode_home(seq=0):
    return _encode({"cmd": "home", "seq": seq})


def encode_ping(seq=0):
    return _encode({"cmd": "ping", "seq": seq})


def parse_telemetry(line):
    """Parse one line of ESP32->Jetson telemetry/ack JSON.

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
        )
    except (KeyError, TypeError, ValueError):
        return None
