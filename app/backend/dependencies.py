"""Shared, app-lifetime singletons: the vision Pipeline and its FaceRepository.

Stored on app.state (set in main.py's lifespan) and exposed here as
FastAPI dependencies so routers don't import main directly.
"""

from fastapi import Request

from vision.pipeline import Pipeline
from vision.storage.repository import FaceRepository


def get_pipeline(request: Request) -> Pipeline:
    return request.app.state.pipeline


def get_repository(request: Request) -> FaceRepository:
    return request.app.state.repository


def get_current_user():
    """No-op auth stub — MVP is LAN-only with no authentication (see
    AGENTS.md). Kept so routes don't need rewriting when auth is added."""
    return None
