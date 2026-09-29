"""Persistent, validated motor speed profiles; no web dependencies (Python 3.6)."""
import json
import logging
import os
import tempfile
import threading


class MotorSettings(object):
    def __init__(self, path=None):
        self._path = path
        self._lock = threading.Lock()
        self._profiles = {"manual": {"pan": 160, "tilt": 160, "pan_acceleration": 400, "tilt_acceleration": 400},
                          "automatic": {"pan": 40, "tilt": 40, "pan_acceleration": 40, "tilt_acceleration": 40}}
        if path and os.path.exists(path):
            try:
                with open(path) as source:
                    profiles = json.load(source)
                for profile in self._profiles:
                    for axis in ("pan", "tilt"):
                        profiles[profile].setdefault(axis + "_acceleration", self._profiles[profile][axis + "_acceleration"])
                    self._validate(profile, profiles[profile])
                self._profiles = {p: dict(profiles[p]) for p in self._profiles}
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                logging.getLogger(__name__).warning("Invalid motor settings; using defaults")

    @staticmethod
    def _validate(profile, speeds):
        if profile not in ("manual", "automatic") or not isinstance(speeds, dict):
            raise ValueError("invalid speed profile")
        if set(speeds) != {"pan", "tilt", "pan_acceleration", "tilt_acceleration"}:
            raise ValueError("pan and tilt are required")
        for key, value in speeds.items():
            maximum = 20000 if key.endswith("_acceleration") else 4000
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("invalid speed or acceleration")

    def get(self, profile):
        with self._lock:
            return dict(self._profiles[profile])

    def all(self):
        with self._lock:
            return {p: dict(v) for p, v in self._profiles.items()}

    def set(self, profile, speeds):
        self._validate(profile, speeds)
        with self._lock:
            updated = {p: dict(v) for p, v in self._profiles.items()}
            updated[profile] = dict(speeds)
            if self._path:
                directory = os.path.dirname(os.path.abspath(self._path))
                os.makedirs(directory, exist_ok=True)
                fd, temporary = tempfile.mkstemp(dir=directory, prefix="motor-speeds-", suffix=".tmp")
                try:
                    with os.fdopen(fd, "w") as target:
                        json.dump(updated, target)
                    os.replace(temporary, self._path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            self._profiles = updated
        return self.all()


class StepLimits(MotorSettings):
    """Separate persistent step envelope for calibration commands."""
    def __init__(self, path=None):
        self._path = path
        self._lock = threading.Lock()
        self._profiles = {"limits": {"pan_min": 0, "pan_max": 12000,
                                     "tilt_min": -1500, "tilt_max": 1500}}
        if path and os.path.exists(path):
            with open(path) as source:
                loaded = json.load(source)
            self._validate("limits", loaded["limits"])
            self._profiles = loaded

    @staticmethod
    def _validate(profile, values):
        if profile != "limits" or set(values) != {"pan_min", "pan_max", "tilt_min", "tilt_max"}:
            raise ValueError("Se requieren los cuatro límites")
        for value in values.values():
            if type(value) is not int or not -200000 <= value <= 200000:
                raise ValueError("Los límites deben ser enteros entre -200000 y 200000")
        for axis in ("pan", "tilt"):
            low, high = values[axis + "_min"], values[axis + "_max"]
            if not low <= 0 <= high or low >= high:
                raise ValueError("Cada intervalo debe contener cero y mínimo < máximo")
