"""Pydantic models for the Ai-RMY API. Mirrors app/frontend/src/types/api.ts —
keep both in sync when this changes."""

from typing import List, Optional

from pydantic import BaseModel


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class PersonOut(BaseModel):
    id: int
    name: str
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
    frame_width: int
    frame_height: int
    detection: Optional[DetectionOut] = None
    telemetry: Optional[TelemetryOut] = None
    serial_connected: bool
    tracking_enabled: bool


class GimbalStatusOut(BaseModel):
    serial_connected: bool
    tracking_enabled: bool
    telemetry: Optional[TelemetryOut] = None


class TrackingModeIn(BaseModel):
    enabled: bool


class HealthOut(BaseModel):
    status: str
    version: str
