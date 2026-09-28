import cv2
import numpy as np
import pytest

from vision.config import ObjectDetectionConfig
from vision.detection.objects import ObjectDetector

# Smallest input size that still exercises every stride (8, 16, 32, 64) with
# a single 1x1 grid cell at stride=64, so the crafted outputs stay tiny.
_INPUT_SIZE = 64
_PERSON_INDEX = 0  # COCO_LABELS[0]
_BICYCLE_INDEX = 1  # COCO_LABELS[1]


def _feat_cells(stride):
    return (_INPUT_SIZE // stride) ** 2


class _FakeNet(object):
    def __init__(self, outputs):
        self._outputs = outputs

    def setInput(self, blob):
        pass

    def getUnconnectedOutLayersNames(self):
        return ["out%d" % i for i in range(len(self._outputs))]

    def forward(self, names):
        return self._outputs


def _build_outputs(stride64_label_index=None, stride64_score=0.0):
    """Builds the 8 (cls_score, bbox_pred) tensors the net.forward() call
    returns, one pair per stride in (8, 16, 32, 64) order. All anchors are
    zeroed except optionally a single one at the lone stride=64 grid cell,
    whose all-zero bbox_pred decodes (via the softmax+DFL integral) to a
    fixed box spanning the entire letterboxed 64x64 input -- see
    detection/objects.py's `_decode_stride` docstring-level comments."""
    outputs = []
    for stride in (8, 16, 32, 64):
        cells = _feat_cells(stride)
        cls_score = np.zeros((1, cells, 80), dtype=np.float32)
        bbox_pred = np.zeros((1, cells, 4, 8), dtype=np.float32)
        if stride == 64 and stride64_label_index is not None:
            cls_score[0, 0, stride64_label_index] = stride64_score
        outputs.append(cls_score)
        outputs.append(bbox_pred)
    return outputs


def _detector(monkeypatch, outputs, **config_overrides):
    config = ObjectDetectionConfig(
        model_path="unused",
        score_threshold=config_overrides.pop("score_threshold", 0.5),
        nms_threshold=config_overrides.pop("nms_threshold", 0.5),
        input_size=(_INPUT_SIZE, _INPUT_SIZE),
    )
    monkeypatch.setattr(cv2.dnn, "readNet", lambda path: _FakeNet(outputs))
    return ObjectDetector(config)


def test_detect_returns_labeled_detection_above_threshold(monkeypatch):
    outputs = _build_outputs(stride64_label_index=_PERSON_INDEX, stride64_score=0.9)
    detector = _detector(monkeypatch, outputs)
    frame = np.zeros((_INPUT_SIZE, _INPUT_SIZE, 3), dtype=np.uint8)

    detections = detector.detect(frame)

    assert len(detections) == 1
    detection = detections[0]
    assert detection.label == "person"
    assert detection.score == pytest.approx(0.9)
    # Square frame == input_size, so letterboxing is a no-op: the decoded
    # box (spanning the whole padded input) maps back to the whole frame.
    assert detection.bbox == pytest.approx((0.0, 0.0, float(_INPUT_SIZE), float(_INPUT_SIZE)))


def test_detect_drops_detections_below_score_threshold(monkeypatch):
    outputs = _build_outputs(stride64_label_index=_PERSON_INDEX, stride64_score=0.1)
    detector = _detector(monkeypatch, outputs, score_threshold=0.5)
    frame = np.zeros((_INPUT_SIZE, _INPUT_SIZE, 3), dtype=np.uint8)

    assert detector.detect(frame) == []


def test_detect_unletterboxes_non_square_frame(monkeypatch):
    outputs = _build_outputs(stride64_label_index=_BICYCLE_INDEX, stride64_score=0.9)
    detector = _detector(monkeypatch, outputs)
    # Half-height frame: letterboxed with vertical padding, so the decoded
    # full-input box must be cropped back to the original aspect ratio.
    frame = np.zeros((_INPUT_SIZE // 2, _INPUT_SIZE, 3), dtype=np.uint8)

    detections = detector.detect(frame)

    assert len(detections) == 1
    detection = detections[0]
    assert detection.label == "bicycle"
    assert detection.bbox == pytest.approx((0.0, 0.0, float(_INPUT_SIZE), float(_INPUT_SIZE // 2)))
