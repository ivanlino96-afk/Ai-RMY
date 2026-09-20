from vision.config import TrackingConfig
from vision.tracking.controller import PixelOffset, TrackingController


def make_controller(**overrides):
    config = TrackingConfig(**overrides) if overrides else TrackingConfig()
    return TrackingController(config)


def test_centered_offset_within_deadband_returns_none():
    controller = make_controller()
    offset = PixelOffset(dx=1, dy=1, frame_width=640, frame_height=480)
    assert controller.compute(offset) is None


def test_offset_right_of_center_pans_right():
    controller = make_controller()
    offset = PixelOffset(dx=200, dy=0, frame_width=640, frame_height=480)
    delta = controller.compute(offset)
    assert delta is not None
    assert delta.pan_deg > 0
    assert delta.tilt_deg == 0


def test_offset_below_center_tilts_down():
    controller = make_controller()
    offset = PixelOffset(dx=0, dy=150, frame_width=640, frame_height=480)
    delta = controller.compute(offset)
    assert delta is not None
    assert delta.tilt_deg > 0
    assert delta.pan_deg == 0


def test_offset_left_and_above_center_is_negative_both_axes():
    controller = make_controller()
    offset = PixelOffset(dx=-200, dy=-150, frame_width=640, frame_height=480)
    delta = controller.compute(offset)
    assert delta.pan_deg < 0
    assert delta.tilt_deg < 0


def test_large_offset_clamped_to_max_delta_deg():
    controller = make_controller(max_delta_deg=3.0, gain_pan_deg=100.0, gain_tilt_deg=100.0)
    offset = PixelOffset(dx=320, dy=240, frame_width=640, frame_height=480)
    delta = controller.compute(offset)
    assert delta.pan_deg == 3.0
    assert delta.tilt_deg == 3.0


def test_zero_size_frame_returns_none():
    controller = make_controller()
    offset = PixelOffset(dx=10, dy=10, frame_width=0, frame_height=0)
    assert controller.compute(offset) is None
