"""Central configuration for the vision pipeline.

Kept dependency-free (no cv2/onnxruntime/pyserial imports) so it can be
imported anywhere, including tests, without the heavy CV stack installed.

Python 3.6 compatible: NamedTuple instead of dataclasses.
"""

from typing import NamedTuple, Tuple

# Mirrors firmware/src/main.cpp's kLimits -- the Arduino MKR Zero remains the sole
# enforcement authority (see AGENTS.md); this is only used to avoid starting
# a scan whose configured range would silently truncate at the firmware
# boundary.
FIRMWARE_PAN_LIMITS_DEG = (-45.0, 45.0)
FIRMWARE_TILT_LIMITS_DEG = (-30.0, 30.0)


class CameraConfig(NamedTuple):
    device_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30


class DetectionConfig(NamedTuple):
    model_path: str = "vision/models/yunet.onnx"
    score_threshold: float = 0.8
    nms_threshold: float = 0.3
    top_k: int = 20


class RecognitionConfig(NamedTuple):
    model_path: str = "vision/models/w600k_mbf.onnx"
    input_size: int = 112
    # Cosine similarity >= this counts as a match. Empirically calibrated for
    # the w600k_mbf (MobileFaceNet) model: genuine same-person cross-pose
    # similarity from real captures lands around 0.5-0.7, not 0.9+, so 0.90
    # made every match (and every enrollment, see below) unreachable.
    match_threshold: float = 0.45
    # Minimum cross-photo cosine similarity required between the 3 enrollment
    # photos for the enrollment to be accepted (RF-5). Shared with
    # match_threshold by design (see specs/plan.md) to avoid an unjustified
    # second metric.
    enrollment_consistency_threshold: float = 0.45
    # Recognition is far more expensive than detection, so it only runs
    # every Nth frame on the currently tracked face crop.
    run_every_n_frames: int = 5
    # How long a recognized identity is kept for a face that leaves and
    # re-enters frame, instead of being re-evaluated as a new detection
    # (RF-14).
    identity_memory_seconds: float = 30.0


class TrackingConfig(NamedTuple):
    # Fraction of frame half-width/half-height treated as "already centered"
    # -> no correction sent. Prevents hunting/jitter around dead-center.
    deadband_fraction: float = 0.05
    # Proportional gain: degrees of pan/tilt correction per normalized pixel
    # offset (offset in [-1, 1] relative to frame half-size).
    gain_pan_deg: float = -30.0
    gain_tilt_deg: float = 25.0
    # Per-tick cap so a single correction can't be huge (e.g. detection
    # jumping to a different face). Enforced here in addition to the
    # firmware's own soft limits.
    max_delta_deg: float = 15.0


class SerialLinkConfig(NamedTuple):
    port: str = "/dev/gimbal"
    baudrate: int = 115200
    # How long to wait for a line before considering the read a timeout.
    read_timeout_s: float = 0.5
    # Backoff schedule (seconds) when the serial device disappears.
    reconnect_backoff_s: "tuple" = (0.5, 1.0, 2.0, 5.0)
    ping_interval_s: float = 2.0


class StorageConfig(NamedTuple):
    db_path: str = "vision/data/faces.db"
    photos_dir: str = "vision/data/faces"
    alarms_dir: str = "vision/data/alarms"


class ObjectDetectionConfig(NamedTuple):
    model_path: str = "vision/models/nanodet.onnx"
    # Matches the official NanoDet-Plus demo's own defaults (opencv_zoo
    # object_detection_nanodet demo.py, 2022nov export).
    score_threshold: float = 0.35
    nms_threshold: float = 0.6
    input_size: Tuple[int, int] = (416, 416)


class ScanConfig(NamedTuple):
    # Angular sweep for the room-scan / angular object inventory feature
    # (2D pan/tilt grid -- not a 3D/distance map, see specs/tasks.md).
    pan_range_deg: Tuple[float, float] = (-45.0, 45.0)
    tilt_range_deg: Tuple[float, float] = (-30.0, 30.0)
    step_deg: float = 15.0
    # Settle + detect time per waypoint, once the gimbal reports arrival.
    dwell_s: float = 1.5
    arrival_timeout_s: float = 5.0


class DefenseModeConfig(NamedTuple):
    # How long a single suspect must stay continuously unidentified before
    # the threat alarm fires (one photo + one log entry per sighting).
    threat_seconds: float = 3.0
    # Same center-distance correlation criterion as _IdentityMemory, used
    # here to tell "the same unrecognized face across frames" apart from a
    # new sighting.
    max_center_distance: float = 75.0
    # How long a sighting can go unseen before it's dropped -- a face that
    # reappears after this counts as a brand new sighting (re-arms the
    # alarm).
    sighting_timeout_s: float = 1.0
    # Once a threat photo is taken near a given bbox position, suppress
    # further photos there for this long -- even if the sighting itself
    # times out and re-arms in between (head turns, brief occlusion, a
    # missed detection frame). One photo per intrusion, not one per
    # sighting-timeout gap, for as long as the suspect keeps reappearing in
    # roughly the same spot.
    alarm_photo_cooldown_s: float = 600.0
    log_max_events: int = 100


def validate_scan_config(scan_config):
    """Clamps pan/tilt_range_deg to the firmware's soft limits. UX-only --
    the Arduino MKR Zero re-validates every goto regardless (see AGENTS.md)."""
    pan_lo, pan_hi = scan_config.pan_range_deg
    tilt_lo, tilt_hi = scan_config.tilt_range_deg
    fw_pan_lo, fw_pan_hi = FIRMWARE_PAN_LIMITS_DEG
    fw_tilt_lo, fw_tilt_hi = FIRMWARE_TILT_LIMITS_DEG
    return scan_config._replace(
        pan_range_deg=(max(pan_lo, fw_pan_lo), min(pan_hi, fw_pan_hi)),
        tilt_range_deg=(max(tilt_lo, fw_tilt_lo), min(tilt_hi, fw_tilt_hi)),
    )


class PipelineConfig(NamedTuple):
    camera: CameraConfig = CameraConfig()
    detection: DetectionConfig = DetectionConfig()
    recognition: RecognitionConfig = RecognitionConfig()
    tracking: TrackingConfig = TrackingConfig()
    serial_link: SerialLinkConfig = SerialLinkConfig()
    storage: StorageConfig = StorageConfig()
    object_detection: ObjectDetectionConfig = ObjectDetectionConfig()
    scan: ScanConfig = ScanConfig()
    defense: DefenseModeConfig = DefenseModeConfig()
    # Reduced-rate JPEG stream for the MJPEG endpoint (viewers don't need
    # full capture FPS).
    stream_fps: int = 12
