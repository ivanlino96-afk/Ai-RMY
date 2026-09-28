from fastapi import APIRouter, Depends

from app.backend.dependencies import get_pipeline
from app.backend.schemas import CameraInfo, CameraListOut, CameraSelectIn

router = APIRouter(prefix="/api/camera", tags=["camera"])


@router.get("/list", response_model=CameraListOut)
def camera_list(pipeline=Depends(get_pipeline)):
    return CameraListOut(cameras=[CameraInfo(**camera) for camera in pipeline.list_cameras()])


@router.post("/select")
def camera_select(payload: CameraSelectIn, pipeline=Depends(get_pipeline)):
    pipeline.select_camera(payload.device_index)
    return {"ok": True, "device_index": payload.device_index}
