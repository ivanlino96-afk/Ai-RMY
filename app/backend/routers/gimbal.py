from fastapi import APIRouter, Depends

from app.backend.dependencies import get_pipeline
from app.backend.schemas import GimbalStatusOut, JogIn, TelemetryOut, TrackingModeIn

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


@router.post("/gimbal/home")
def gimbal_home(pipeline=Depends(get_pipeline)):
    pipeline.home()
    return {"ok": True}


@router.post("/tracking/mode")
def set_tracking_mode(payload: TrackingModeIn, pipeline=Depends(get_pipeline)):
    ok = pipeline.set_tracking_enabled(payload.enabled)
    return {"ok": ok, "tracking_enabled": pipeline.tracking_enabled}


@router.post("/gimbal/jog")
def gimbal_jog(payload: JogIn, pipeline=Depends(get_pipeline)):
    sent = pipeline.jog(payload.pan_deg, payload.tilt_deg)
    return {"ok": sent}


@router.post("/gimbal/stop")
def gimbal_stop(pipeline=Depends(get_pipeline)):
    pipeline.emergency_stop()
    return {"ok": True}
