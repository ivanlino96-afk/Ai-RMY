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


def get_enrollment_sessions(connection: HTTPConnection) -> dict:
    """In-memory {session_id: {"session": EnrollmentSession, "person_id":
    int | None}} store for guided-capture sessions (T14/T16). Ephemeral by
    design (see vision/enroll.py) -- lost on restart, which is fine since an
    abandoned session must leave no trace anyway."""
    return connection.app.state.enrollment_sessions


def get_current_user():
    """No-op auth stub — MVP is LAN-only with no authentication (see
    AGENTS.md). Kept so routes don't need rewriting when auth is added."""
    return None
