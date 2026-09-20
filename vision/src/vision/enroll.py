"""One-shot face enrollment: turn a single uploaded photo into an embedding.

Separate from Pipeline (which owns long-running detector/embedder instances
on its background thread) because enrollment happens on-demand from an API
request, not once per frame — see app/backend/routers/people.py.
"""

from vision.config import DetectionConfig, RecognitionConfig
from vision.detection.yunet import YuNetDetector
from vision.recognition.embedder import FaceEmbedder


class NoFaceDetected(Exception):
    pass


def embed_face_from_image_bytes(
    image_bytes, detection_config=None, recognition_config=None
):
    """Decodes an image, detects the largest face, and returns its embedding.

    Raises NoFaceDetected if no face is found — callers (the people-photos
    endpoint) should reject the upload rather than store a bogus embedding.
    """
    import cv2
    import numpy as np

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise NoFaceDetected("could not decode image")

    height, width = frame.shape[:2]
    detector = YuNetDetector(detection_config or DetectionConfig(), frame_size=(width, height))
    detections = detector.detect(frame)
    if not detections:
        raise NoFaceDetected("no face detected in image")

    target = detections[0]
    embedder = FaceEmbedder(recognition_config or RecognitionConfig())
    return embedder.embed_from_landmarks(frame, target.landmarks)
