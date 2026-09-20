"""Shared, app-lifetime singletons: the vision Pipeline and its FaceRepository.

Stored on app.state (set in main.py's lifespan) and exposed here as
FastAPI dependencies so routers don't import main directly.
"""

from starlette.requests import HTTPConnection

from vision.pipeline import Pipeline
from vision.storage.repository import FaceRepository


def get_pipeline(connection: HTTPConnection) -> Pipeline:
    """Typed as HTTPConnection (the base both Request and WebSocket share) so
    this dependency resolves in the /api/ws/events WebSocket route too, not
    just plain HTTP requests."""
    return connection.app.state.pipeline


def get_repository(connection: HTTPConnection) -> FaceRepository:
    return connection.app.state.repository


def get_current_user():
    """No-op auth stub — MVP is LAN-only with no authentication (see
    AGENTS.md). Kept so routes don't need rewriting when auth is added."""
    return None
