from fastapi import APIRouter, Depends

from app.backend.dependencies import get_pipeline
from app.backend.schemas import ScanConfigIn, ScanStatusOut

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/start")
def scan_start(payload: ScanConfigIn, pipeline=Depends(get_pipeline)):
    started = pipeline.start_scan(
        pan_range_deg=payload.pan_range_deg,
        tilt_range_deg=payload.tilt_range_deg,
        step_deg=payload.step_deg,
    )
    return {"ok": started}


@router.post("/cancel")
def scan_cancel(pipeline=Depends(get_pipeline)):
    pipeline.cancel_scan()
    return {"ok": True}


@router.get("/status", response_model=ScanStatusOut)
def scan_status(pipeline=Depends(get_pipeline)):
    return pipeline.scan_status()
