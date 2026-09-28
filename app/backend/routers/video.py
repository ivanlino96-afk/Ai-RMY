import asyncio

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.backend.dependencies import get_pipeline

router = APIRouter(prefix="/api/stream", tags=["video"])

_BOUNDARY = "frame"


@router.get("/video")
def stream_video(pipeline=Depends(get_pipeline)):
    interval = 1.0 / max(pipeline.config.stream_fps, 1)

    async def generate():
        while True:
            jpeg = pipeline.state.latest_jpeg()
            if jpeg is not None:
                yield (
                    b"--" + _BOUNDARY.encode() + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                    + jpeg + b"\r\n"
                )
            await asyncio.sleep(interval)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=%s" % _BOUNDARY,
        # Without this, the browser can serve a cached copy of this response
        # (i.e. a single frozen frame) to a new <img> element that remounts
        # with the same src -- exactly what happens navigating away from and
        # back to the live view. Every mount must open a fresh live stream.
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )
