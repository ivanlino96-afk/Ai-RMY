"""Pydantic models for the Ai-RMY API. Mirrors app/frontend/src/types/api.ts —
keep both in sync when this changes."""

import re
from typing import List, Optional

from pydantic import BaseModel, field_validator

# RF-17: a permissive but real format check -- this rejects typos, not
# international phone number rules the MVP doesn't need to enforce.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[0-9+()\-\s]+$")


def _validate_email(value):
    if not _EMAIL_RE.match(value):
        raise ValueError("correo inválido: debe tener el formato nombre@dominio.tld")
    return value


def _validate_phone(value):
    if not _PHONE_RE.match(value) or not any(ch.isdigit() for ch in value):
        raise ValueError("teléfono inválido: solo dígitos, espacios y + ( ) -")
    return value


class PersonIn(BaseModel):
    name: str
    age: Optional[int] = None
    email: str = ""
    phone: str = ""
    notes: str = ""

    _validate_email = field_validator("email")(lambda v: _validate_email(v) if v else v)
    _validate_phone = field_validator("phone")(lambda v: _validate_phone(v) if v else v)


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

    _validate_email = field_validator("email")(
        lambda v: _validate_email(v) if v is not None else v
    )
    _validate_phone = field_validator("phone")(
        lambda v: _validate_phone(v) if v is not None else v
    )


class PersonOut(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    email: str
    phone: str
    notes: str
    created_at: float


class DetectionOut(BaseModel):
    bbox: List[float]
    score: float
    label: Optional[str] = None


class TelemetryOut(BaseModel):
    calibration: bool = False
    pan_steps: int = 0
    tilt_steps: int = 0
    ok: bool
    pan_deg: float
    tilt_deg: float
    moving: bool
    homed: bool


class TrackingOffsetOut(BaseModel):
    dx: float
    dy: float
    pan_deg: float
    tilt_deg: float
    centered: bool


class CameraInfo(BaseModel):
    index: int
    width: int
    height: int


class CameraListOut(BaseModel):
    cameras: List[CameraInfo] = []


class CameraSelectIn(BaseModel):
    device_index: Optional[int] = None


class ScanConfigIn(BaseModel):
    pan_range_deg: Optional[List[float]] = None
    tilt_range_deg: Optional[List[float]] = None
    step_deg: Optional[float] = None


class ScanObjectOut(BaseModel):
    bbox: List[float]
    label: str
    score: float


class ScanWaypointOut(BaseModel):
    pan_deg: float
    tilt_deg: float
    objects: List[ScanObjectOut] = []


class ScanStatusOut(BaseModel):
    state: str  # idle | running | done
    progress: float = 0.0
    results: List[ScanWaypointOut] = []


class DefenseLogEntryOut(BaseModel):
    type: str  # "identified" | "threat"
    timestamp: float
    name: Optional[str] = None
    photo: Optional[str] = None


class DefenseStatusOut(BaseModel):
    active: bool
    armed_at: Optional[float] = None
    log: List[DefenseLogEntryOut] = []


class EventOut(BaseModel):
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    detections: List[DetectionOut] = []
    telemetry: Optional[TelemetryOut] = None
    serial_connected: bool
    tracking_enabled: bool
    camera_connected: bool = True
    camera_index: Optional[int] = None
    tracking_offset: Optional[TrackingOffsetOut] = None
    scan: Optional[ScanStatusOut] = None
    defense: Optional[DefenseStatusOut] = None


class GimbalStatusOut(BaseModel):
    serial_connected: bool
    tracking_enabled: bool
    telemetry: Optional[TelemetryOut] = None


class TrackingModeIn(BaseModel):
    enabled: bool


class StepJogIn(BaseModel):
    pan_steps: int = 0
    tilt_steps: int = 0

    @field_validator("pan_steps", "tilt_steps", mode="before")
    @classmethod
    def validate_steps(cls, value):
        if type(value) is not int or abs(value) > 2000:
            raise ValueError("Usa enteros entre -2000 y 2000")
        return value


class JogIn(BaseModel):
    pan_deg: float = 0.0
    tilt_deg: float = 0.0


class HealthOut(BaseModel):
    status: str
    version: str


class MotorSpeedsIn(BaseModel):
    pan: int
    tilt: int
    pan_acceleration: int
    tilt_acceleration: int

    @field_validator("pan", "tilt", mode="before")
    @classmethod
    def validate_speed(cls, value):
        if type(value) is not int or not 1 <= value <= 4000:
            raise ValueError("Usa una velocidad entera entre 1 y 4000 pulsos/s")
        return value

    @field_validator("pan_acceleration", "tilt_acceleration", mode="before")
    @classmethod
    def validate_acceleration(cls, value):
        if type(value) is not int or not 1 <= value <= 20000:
            raise ValueError("Usa aceleración entera entre 1 y 20000 pulsos/s²")
        return value


class StepLimitsIn(BaseModel):
    pan_min: int
    pan_max: int
    tilt_min: int
    tilt_max: int

    @field_validator("pan_min", "pan_max", "tilt_min", "tilt_max", mode="before")
    @classmethod
    def validate_limit(cls, value):
        if type(value) is not int or not -200000 <= value <= 200000:
            raise ValueError("Usa pasos enteros entre -200000 y 200000")
        return value
