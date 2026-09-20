"""Face embeddings via a standalone ONNX model (onnxruntime), NOT the
`insightface` pip package — that package fails to build on the Jetson
Nano's Python 3.6/aarch64 (see AGENTS.md, docs/architecture.md). The
model file itself (e.g. `w600k_mbf.onnx` extracted from InsightFace's
`buffalo_sc` pack) is downloaded separately by
`scripts/download_models.sh` and never committed.

cv2/onnxruntime are imported lazily so `vision.recognition` stays
importable without the CV stack installed (see vision/pyproject.toml).

Verification note (see plan's "Verificación" step 3): before wiring this
into the tracking loop, confirm standalone that the model loads and
produces embeddings of the expected dimension for a real face crop.
"""

import numpy as np

from vision.config import RecognitionConfig

# Standard 112x112 ArcFace alignment template (5 landmarks: left eye,
# right eye, nose tip, left mouth corner, right mouth corner).
_REFERENCE_LANDMARKS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class FaceEmbedder(object):
    def __init__(self, config=None):
        import cv2
        import onnxruntime

        self._config = config or RecognitionConfig()
        self._cv2 = cv2
        self._session = onnxruntime.InferenceSession(
            self._config.model_path, providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name

    def align(self, frame, landmarks):
        """Warps the face defined by 5 landmarks to a canonical 112x112 crop."""
        cv2 = self._cv2
        src = np.array(landmarks, dtype=np.float32)
        size = self._config.input_size
        dst = _REFERENCE_LANDMARKS * (size / 112.0)
        matrix, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
        if matrix is None:
            raise ValueError("could not estimate alignment transform from landmarks")
        return cv2.warpAffine(frame, matrix, (size, size), borderValue=0.0)

    def embed(self, face_crop):
        """Returns a 1-D float32 embedding vector for an aligned face crop."""
        blob = self._preprocess(face_crop)
        outputs = self._session.run(None, {self._input_name: blob})
        return outputs[0].reshape(-1).astype(np.float32)

    def embed_from_landmarks(self, frame, landmarks):
        return self.embed(self.align(frame, landmarks))

    def _preprocess(self, face_crop):
        cv2 = self._cv2
        size = self._config.input_size
        if face_crop.shape[0] != size or face_crop.shape[1] != size:
            face_crop = cv2.resize(face_crop, (size, size))
        rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        normalized = (rgb.astype(np.float32) - 127.5) / 128.0
        chw = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(chw, axis=0)
