"""Shared cosine similarity helper.

Extracted so `FaceRepository` (matching stored people against a live
embedding) and `EnrollmentSession` (RF-5's cross-photo consistency check)
don't each re-implement the same coseno math (see docs/constitution.md's
"stack minimo" principle).
"""

import numpy as np


def cosine_similarity(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
