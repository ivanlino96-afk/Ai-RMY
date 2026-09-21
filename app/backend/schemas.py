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
    age: int
    email: str
    phone: str
    notes: str = ""

    _validate_email = field_validator("email")(_validate_email)
    _validate_phone = field_validator("phone")(_validate_phone)


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
    age: int
    email: str
    phone: str
    notes: str
    created_at: float


class DetectionOut(BaseModel):
    bbox: List[float]
    score: float
    label: Optional[str] = None


class TelemetryOut(BaseModel):
    ok: bool
    pan_deg: float
    tilt_deg: float
    moving: bool
    homed: bool


class EventOut(BaseModel):
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    detections: List[DetectionOut] = []
    telemetry: Optional[TelemetryOut] = None
    serial_connected: bool
    tracking_enabled: bool
    camera_connected: bool = True


class GimbalStatusOut(BaseModel):
    serial_connected: bool
    tracking_enabled: bool
    telemetry: Optional[TelemetryOut] = None


class TrackingModeIn(BaseModel):
    enabled: bool


class HealthOut(BaseModel):
    status: str
    version: str
