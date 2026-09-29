from fastapi import APIRouter, Depends, HTTPException

from app.backend.dependencies import get_pipeline
from app.backend.schemas import GimbalStatusOut, StepLimitsIn, JogIn, MotorSpeedsIn, StepJogIn, TelemetryOut, TrackingModeIn

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
            calibration=telemetry.calibration,
            pan_steps=telemetry.pan_steps,
            tilt_steps=telemetry.tilt_steps,
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


@router.post("/gimbal/steps")
def gimbal_steps(payload: StepJogIn, pipeline=Depends(get_pipeline)):
    if (payload.pan_steps == 0) == (payload.tilt_steps == 0):
        return {"ok": False}
    return {"ok": pipeline.jog_steps(payload.pan_steps, payload.tilt_steps)}


@router.get("/settings/motor-speeds")
def get_motor_speeds(pipeline=Depends(get_pipeline)):
    return pipeline.motor_settings.all()


@router.post("/settings/motor-speeds/{profile}")
def set_motor_speeds(profile: str, payload: MotorSpeedsIn, pipeline=Depends(get_pipeline)):
    if profile not in ("manual", "automatic"):
        raise HTTPException(status_code=400, detail="Perfil de velocidad inválido")
    try:
        return pipeline.motor_settings.set(profile, {"pan": payload.pan, "tilt": payload.tilt,
            "pan_acceleration": payload.pan_acceleration, "tilt_acceleration": payload.tilt_acceleration})
    except OSError:
        raise HTTPException(status_code=500, detail="No se pudo guardar la configuración")


@router.get("/settings/step-limits")
def get_step_limits(pipeline=Depends(get_pipeline)):
    return pipeline.step_limits.get("limits")


@router.post("/settings/step-limits")
def set_step_limits(payload: StepLimitsIn, pipeline=Depends(get_pipeline)):
    telemetry = pipeline.last_telemetry
    if telemetry is not None and telemetry.moving:
        raise HTTPException(status_code=409, detail="Detén los motores antes de cambiar límites")
    values = payload.model_dump()
    try:
        from vision.motor_settings import StepLimits
        StepLimits._validate("limits", values)
        if telemetry is not None and not (values["pan_min"] <= telemetry.pan_steps <= values["pan_max"] and values["tilt_min"] <= telemetry.tilt_steps <= values["tilt_max"]):
            raise ValueError("La posición actual queda fuera de los límites propuestos")
        return pipeline.step_limits.set("limits", values)["limits"]
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except OSError:
        raise HTTPException(status_code=500, detail="No se pudieron guardar los límites")
