import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.backend.routers import events, gimbal, people, video
from app.backend.schemas import HealthOut
from vision import __version__ as vision_version
from vision.config import PipelineConfig
from vision.pipeline import Pipeline
from vision.storage.repository import FaceRepository

FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = PipelineConfig()
    repository = FaceRepository(config.storage)
    pipeline = Pipeline(config=config, repository=repository)
    app.state.repository = repository
    app.state.pipeline = pipeline
    pipeline.start()
    try:
        yield
    finally:
        pipeline.stop()
        repository.close()


app = FastAPI(title="Ai-RMY", lifespan=lifespan)

app.include_router(video.router)
app.include_router(events.router)
app.include_router(people.router)
app.include_router(gimbal.router)


@app.get("/api/health", response_model=HealthOut)
def health():
    return HealthOut(status="ok", version=vision_version)


# Serve the built React SPA if present (production). In development the
# Vite dev server runs separately with a proxy to this backend instead.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
