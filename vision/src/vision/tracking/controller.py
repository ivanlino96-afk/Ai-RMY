"""Visual-servoing controller: pixel offset -> pan/tilt delta (degrees).

Proportional control with a deadband around dead-center. No PID: the plan
is to only add integral/derivative terms if bench testing shows steady-
state offset or oscillation (see AGENTS.md) — not speculatively.

Pure math, no cv2/serial dependency, so it's cheap to unit test.
"""

from typing import NamedTuple, Optional

from vision.config import TrackingConfig


class PixelOffset(NamedTuple):
    """Offset of a detection's center from the frame's center, in pixels.

    Positive dx = target is to the right of center; positive dy = target
    is below center (image coordinate origin top-left, per AGENTS.md).
    """

    dx: float
    dy: float
    frame_width: int
    frame_height: int


class PanTiltDelta(NamedTuple):
    pan_deg: float
    tilt_deg: float


def _clamp(value, limit):
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


class TrackingController(object):
    def __init__(self, config=None):
        self._config = config or TrackingConfig()

    def compute(self, offset):
        """Compute a pan/tilt correction for one detection offset.

        Returns None if the offset is within the deadband (no correction
        needed) — callers should send nothing to the ESP32 in that case
        rather than a zero-delta command.
        """
        half_w = offset.frame_width / 2.0
        half_h = offset.frame_height / 2.0
        if half_w <= 0 or half_h <= 0:
            return None

        norm_x = offset.dx / half_w
        norm_y = offset.dy / half_h

        deadband = self._config.deadband_fraction
        if abs(norm_x) < deadband and abs(norm_y) < deadband:
            return None

        # Positive norm_x (target right of center) should pan the camera
        # right to re-center it.
        pan = norm_x * self._config.gain_pan_deg
        tilt = norm_y * self._config.gain_tilt_deg

        pan = _clamp(pan, self._config.max_delta_deg)
        tilt = _clamp(tilt, self._config.max_delta_deg)

        return PanTiltDelta(pan_deg=pan, tilt_deg=tilt)
