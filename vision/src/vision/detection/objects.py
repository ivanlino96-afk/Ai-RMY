"""Generic object detection via NanoDet-Plus-m-1.5x-416 (ONNX, OpenCV Zoo).

cv2 is imported lazily (see vision/pyproject.toml) so `vision.detection` stays
importable without OpenCV installed.

This is an independent reimplementation of the pre/post-processing in
`opencv_zoo/models/object_detection_nanodet/{nanodet.py,demo.py}` (2022nov
export) using only `cv2.dnn`, not that repo's own NanoDet class. The decode
math below (letterbox padding, per-channel mean/std, per-stride anchor
points, DFL integral box regression) was reverse-engineered from that source
and must match it exactly to produce sane boxes -- see the manual smoke-test
step in specs/tasks.md before trusting this against the real model file.
"""

import threading
from typing import NamedTuple, Tuple

import numpy as np

from vision.config import ObjectDetectionConfig

# Standard COCO-80 category order (same as YOLO/COCO-style demos, including
# opencv_zoo's own demo.py, which hardcodes this exact list -- no separate
# labels file ships with the model).
COCO_LABELS = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
)

_STRIDES = (8, 16, 32, 64)
_REG_MAX = 7
# Per-channel normalization, applied to the RGB (not BGR) image -- do not
# "correct" this to look like the usual ImageNet RGB mean, it's applied
# positionally to match the original export exactly.
_MEAN = np.array([103.53, 116.28, 123.675], dtype=np.float32)
_STD = np.array([57.375, 57.12, 58.395], dtype=np.float32)


class ObjectDetection(NamedTuple):
    # (x, y, w, h) in pixels, origin top-left, in the original frame's space.
    bbox: Tuple[float, float, float, float]
    label: str
    score: float


def _letterbox(rgb_image, target_size):
    height, width = rgb_image.shape[:2]
    hw_scale = height / float(width)
    if hw_scale > 1:
        new_height = target_size
        new_width = int(target_size / hw_scale)
        resized = _cv2().resize(rgb_image, (new_width, new_height), interpolation=_cv2().INTER_AREA)
        left = int((target_size - new_width) * 0.5)
        right = target_size - new_width - left
        padded = _cv2().copyMakeBorder(resized, 0, 0, left, right, _cv2().BORDER_CONSTANT, value=0)
        top = 0
    else:
        new_width = target_size
        new_height = int(target_size * hw_scale)
        resized = _cv2().resize(rgb_image, (new_width, new_height), interpolation=_cv2().INTER_AREA)
        top = int((target_size - new_height) * 0.5)
        bottom = target_size - new_height - top
        padded = _cv2().copyMakeBorder(resized, top, bottom, 0, 0, _cv2().BORDER_CONSTANT, value=0)
        left = 0
    return padded, (top, left, new_height, new_width)


def _unletterbox_box(box, original_shape, letterbox_scale):
    height, width = original_shape
    top, left, new_height, new_width = letterbox_scale
    x1, y1, x2, y2 = box
    if height == width:
        ratio = height / float(new_height)
        x1, x2 = x1 * ratio, x2 * ratio
        y1, y2 = y1 * ratio, y2 * ratio
    else:
        ratio_h = height / float(new_height)
        ratio_w = width / float(new_width)
        x1 = (x1 - left) * ratio_w
        x2 = (x2 - left) * ratio_w
        y1 = (y1 - top) * ratio_h
        y2 = (y2 - top) * ratio_h
    x1 = min(max(x1, 0.0), float(width))
    x2 = min(max(x2, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    y2 = min(max(y2, 0.0), float(height))
    return x1, y1, x2, y2


def _softmax_last_axis(x):
    # Plain exp/sum, deliberately without max-subtraction for numerical
    # stability -- must match the original export bit-for-bit in shape.
    exp = np.exp(x)
    return exp / exp.sum(axis=-1, keepdims=True)


def _decode_stride(cls_score, bbox_pred, stride, input_size):
    feat_w = input_size // stride
    feat_h = input_size // stride
    shift_x = np.arange(feat_w) * stride
    shift_y = np.arange(feat_h) * stride
    xv, yv = np.meshgrid(shift_x, shift_y)
    cx = xv + 0.5 * (stride - 1)
    cy = yv + 0.5 * (stride - 1)
    points = np.stack([cx, cy], axis=-1).reshape(-1, 2).astype(np.float32)

    cls_score = np.asarray(cls_score).reshape(-1, len(COCO_LABELS))
    bbox_pred = np.asarray(bbox_pred).reshape(-1, 4, _REG_MAX + 1)

    distribution = _softmax_last_axis(bbox_pred)
    project = np.arange(_REG_MAX + 1, dtype=np.float32)
    distances = distribution.dot(project) * stride  # (N, 4): l, t, r, b

    x1 = points[:, 0] - distances[:, 0]
    y1 = points[:, 1] - distances[:, 1]
    x2 = points[:, 0] + distances[:, 2]
    y2 = points[:, 1] + distances[:, 3]
    boxes = np.clip(np.stack([x1, y1, x2, y2], axis=-1), 0, input_size)

    return boxes, cls_score


_cv2_module = None


def _cv2():
    return _cv2_module


class ObjectDetector(object):
    def __init__(self, config=None):
        global _cv2_module
        import cv2  # noqa: local import, see module docstring

        _cv2_module = cv2
        self._config = config or ObjectDetectionConfig()
        self._input_size = self._config.input_size[0]
        self._lock = threading.Lock()
        self._net = cv2.dnn.readNet(self._config.model_path)

    def detect(self, frame):
        """Returns a list of ObjectDetection, in original-frame pixel coords."""
        height, width = frame.shape[:2]
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        letterboxed, scale = _letterbox(rgb, self._input_size)
        normalized = (letterboxed.astype(np.float32) - _MEAN) / _STD
        blob = self._cv2.dnn.blobFromImage(normalized)

        with self._lock:
            self._net.setInput(blob)
            outputs = self._net.forward(self._net.getUnconnectedOutLayersNames())

        cls_scores, bbox_preds = outputs[0::2], outputs[1::2]

        all_boxes = []
        all_scores = []
        for stride, cls_score, bbox_pred in zip(_STRIDES, cls_scores, bbox_preds):
            boxes, scores = _decode_stride(cls_score, bbox_pred, stride, self._input_size)
            all_boxes.append(boxes)
            all_scores.append(scores)
        boxes = np.concatenate(all_boxes, axis=0)
        scores = np.concatenate(all_scores, axis=0)

        class_ids = scores.argmax(axis=1)
        confidences = scores.max(axis=1)

        keep = confidences >= self._config.score_threshold
        if not np.any(keep):
            return []
        boxes, confidences, class_ids = boxes[keep], confidences[keep], class_ids[keep]

        boxes_xywh = [
            [float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])] for b in boxes
        ]
        indices = self._cv2.dnn.NMSBoxes(
            boxes_xywh, confidences.tolist(), self._config.score_threshold, self._config.nms_threshold
        )
        if len(indices) == 0:
            return []
        indices = np.asarray(indices).reshape(-1)

        detections = []
        for i in indices:
            x1, y1, x2, y2 = _unletterbox_box(boxes[i], (height, width), scale)
            detections.append(
                ObjectDetection(
                    bbox=(x1, y1, x2 - x1, y2 - y1),
                    label=COCO_LABELS[int(class_ids[i])],
                    score=float(confidences[i]),
                )
            )
        return detections

    @property
    def _cv2(self):
        return _cv2_module
