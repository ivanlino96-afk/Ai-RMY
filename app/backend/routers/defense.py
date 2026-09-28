import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.backend.dependencies import get_pipeline
from app.backend.schemas import DefenseStatusOut

router = APIRouter(prefix="/api/defense", tags=["defense"])


@router.post("/arm")
def defense_arm(pipeline=Depends(get_pipeline)):
    return {"ok": pipeline.start_defense_mode()}


@router.post("/disarm")
def defense_disarm(pipeline=Depends(get_pipeline)):
    pipeline.stop_defense_mode()
    return {"ok": True}


@router.get("/status", response_model=DefenseStatusOut)
def defense_status(pipeline=Depends(get_pipeline)):
    return pipeline.defense_status()


@router.get("/photo/{filename}")
def defense_photo(filename: str, pipeline=Depends(get_pipeline)):
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    path = os.path.join(pipeline.config.storage.alarms_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="alarm photo not found")
    return FileResponse(path, media_type="image/jpeg")
