import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.backend.dependencies import get_pipeline

router = APIRouter(tags=["events"])


@router.websocket("/api/ws/events")
async def events_socket(websocket: WebSocket, pipeline=Depends(get_pipeline)):
    await websocket.accept()
    loop = asyncio.get_event_loop()
    last_sent_version = 0
    try:
        while True:
            event, version = await loop.run_in_executor(
                None, pipeline.state.wait_for_update, last_sent_version, 5.0
            )
            if version != last_sent_version and event is not None:
                await websocket.send_json(event)
            last_sent_version = version
    except WebSocketDisconnect:
        pass
