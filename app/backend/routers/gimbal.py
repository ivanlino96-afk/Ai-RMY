from fastapi import APIRouter, Depends

from app.backend.dependencies import get_pipeline
from app.backend.schemas import GimbalStatusOut, TelemetryOut, TrackingModeIn

router = APIRouter(prefix="/api", tags=["gimbal"])


@router.get("/gimbal/status", response_model=GimbalStatusOut)
def gimbal_status(pipeline=Depends(get_pipeline)):
    telemetry = pipeline.last_telemetry
    return GimbalStatusOut(
        serial_connected=pipeline.serial_connected,
        tracking_enabled=pipeline.tracking_enabled,
        telemetry=None
        if telemetry is None
        else TelemetryOut(
            ok=telemetry.ok,
            pan_deg=telemetry.pan_deg,
            tilt_deg=telemetry.tilt_deg,
            moving=telemetry.moving,
            homed=telemetry.homed,
        ),
    )


@router.post("/gimbal/center")
def gimbal_center(pipeline=Depends(get_pipeline)):
    pipeline.center()
    return {"ok": True}


@router.post("/tracking/mode")
def set_tracking_mode(payload: TrackingModeIn, pipeline=Depends(get_pipeline)):
    pipeline.set_tracking_enabled(payload.enabled)
    return {"ok": True, "tracking_enabled": payload.enabled}
