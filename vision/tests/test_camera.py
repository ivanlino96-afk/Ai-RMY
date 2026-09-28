from vision.capture.camera import list_available_cameras


class _FakeCap(object):
    def __init__(self, opened, width, height):
        self._opened = opened
        self._width = width
        self._height = height
        self.released = False

    def isOpened(self):
        return self._opened

    def get(self, prop):
        return self._width if prop == "W" else self._height

    def release(self):
        self.released = True


class _FakeCv2Module(object):
    CAP_PROP_FRAME_WIDTH = "W"
    CAP_PROP_FRAME_HEIGHT = "H"

    def __init__(self, devices):
        # devices: {index: (width, height)} for indices that open successfully
        self._devices = devices
        self.caps = []

    def VideoCapture(self, index):
        if index in self._devices:
            width, height = self._devices[index]
            cap = _FakeCap(True, width, height)
        else:
            cap = _FakeCap(False, 0, 0)
        self.caps.append(cap)
        return cap


def test_list_available_cameras_reports_only_indexes_that_open():
    fake_cv2 = _FakeCv2Module({0: (640, 480), 2: (1920, 1080)})

    cameras = list_available_cameras(max_index=4, cv2_module=fake_cv2)

    assert cameras == [
        {"index": 0, "width": 640, "height": 480},
        {"index": 2, "width": 1920, "height": 1080},
    ]


def test_list_available_cameras_releases_every_probed_capture():
    fake_cv2 = _FakeCv2Module({0: (640, 480)})

    list_available_cameras(max_index=3, cv2_module=fake_cv2)

    assert all(cap.released for cap in fake_cv2.caps)


def test_list_available_cameras_reports_nothing_when_no_device_opens():
    fake_cv2 = _FakeCv2Module({})

    cameras = list_available_cameras(max_index=4, cv2_module=fake_cv2)

    assert cameras == []
