"""Thin cv2.VideoCapture wrapper.

cv2 is imported lazily (inside __init__, not at module load) so importing
`vision.capture` doesn't require OpenCV to be installed — see
vision/pyproject.toml on why cv2/onnxruntime aren't hard dependencies.
"""

from vision.config import CameraConfig


class Camera(object):
    def __init__(self, config=None):
        import cv2  # noqa: local import, see module docstring

        self._config = config or CameraConfig()
        self._cv2 = cv2
        self._cap = cv2.VideoCapture(self._config.device_index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)
        self._cap.set(cv2.CAP_PROP_FPS, self._config.fps)
        if not self._cap.isOpened():
            raise RuntimeError(
                "could not open camera device index %d" % self._config.device_index
            )

    def read(self):
        """Returns a BGR frame (numpy array), or None if the read failed."""
        ok, frame = self._cap.read()
        if not ok:
            return None
        return frame

    def release(self):
        self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def list_available_cameras(max_index=8, cv2_module=None):
    """Probes device indices [0, max_index) and returns the ones that open,
    as [{"index", "width", "height"}, ...]. `cv2_module` lets tests inject a
    fake without a real camera/OpenCV install (see module docstring)."""
    cv2 = cv2_module
    if cv2 is None:
        import cv2  # noqa: local import, see module docstring

    cameras = []
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        try:
            if cap.isOpened():
                cameras.append(
                    {
                        "index": index,
                        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    }
                )
        finally:
            cap.release()
    return cameras
