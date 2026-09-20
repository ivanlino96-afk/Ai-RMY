"""Central configuration for the vision pipeline.

Kept dependency-free (no cv2/onnxruntime/pyserial imports) so it can be
imported anywhere, including tests, without the heavy CV stack installed.

Python 3.6 compatible: NamedTuple instead of dataclasses.
"""

from typing import NamedTuple


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
    # Cosine similarity >= this counts as a match. Conservative on purpose:
    # prefer "Unknown" over a false positive (see AGENTS.md).
    match_threshold: float = 0.45
    # Recognition is far more expensive than detection, so it only runs
    # every Nth frame on the currently tracked face crop.
    run_every_n_frames: int = 5
    # Consecutive misses before a cached name reverts to "Unknown", so the
    # label doesn't flicker between frames.
    label_decay_frames: int = 8


class TrackingConfig(NamedTuple):
    # Fraction of frame half-width/half-height treated as "already centered"
    # -> no correction sent. Prevents hunting/jitter around dead-center.
    deadband_fraction: float = 0.05
    # Proportional gain: degrees of pan/tilt correction per normalized pixel
    # offset (offset in [-1, 1] relative to frame half-size).
    gain_pan_deg: float = 8.0
    gain_tilt_deg: float = 6.0
    # Per-tick cap so a single correction can't be huge (e.g. detection
    # jumping to a different face). Enforced here in addition to the
    # firmware's own soft limits.
    max_delta_deg: float = 4.0


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


class PipelineConfig(NamedTuple):
    camera: CameraConfig = CameraConfig()
    detection: DetectionConfig = DetectionConfig()
    recognition: RecognitionConfig = RecognitionConfig()
    tracking: TrackingConfig = TrackingConfig()
    serial_link: SerialLinkConfig = SerialLinkConfig()
    storage: StorageConfig = StorageConfig()
    # Reduced-rate JPEG stream for the MJPEG endpoint (viewers don't need
    # full capture FPS).
    stream_fps: int = 12
