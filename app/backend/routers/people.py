"""People CRUD + guided 3-photo enrollment sessions (RF-1 through RF-10).

Enrollment (new person, or RF-8's re-capture-photos-only edit) both go
through the same start/photo/finalize/cancel session flow backed by
`vision.enroll.EnrollmentSession` — see T14/T16 in specs/tasks.md. A session
is purely in-memory (`dependencies.get_enrollment_sessions`) until
`finalize()` succeeds, so a cancelled or abandoned session never touches
`FaceRepository`.
"""

import os
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.backend.dependencies import get_enrollment_sessions, get_pipeline, get_repository
from app.backend.schemas import PersonIn, PersonOut, PersonUpdate
from vision.enroll import (
    EnrollmentSession,
    InconsistentPhotos,
    MultipleFacesDetected,
    NoFaceDetected,
    SessionIncomplete,
    decode_image,
)

router = APIRouter(prefix="/api/people", tags=["people"])


def _to_out(person):
    return PersonOut(
        id=person.id,
        name=person.name,
        age=person.age,
        email=person.email,
        phone=person.phone,
        notes=person.notes,
        created_at=person.created_at,
    )


@router.get("", response_model=List[PersonOut])
def list_people(repository=Depends(get_repository)):
    return [_to_out(p) for p in repository.list_people()]


@router.get("/{person_id}/photo")
def get_person_photo(person_id: int, repository=Depends(get_repository)):
    photo_path = repository.latest_photo_path(person_id)
    if photo_path is None or not os.path.isfile(photo_path):
        raise HTTPException(status_code=404, detail="no photo for this person")
    return FileResponse(photo_path, media_type="image/jpeg")


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(person_id: int, payload: PersonUpdate, repository=Depends(get_repository)):
    """RF-8: editing data never touches photos/embeddings — re-capturing
    photos is the separate /enroll session flow below."""
    if not repository.update_person(
        person_id,
        name=payload.name,
        age=payload.age,
        email=payload.email,
        phone=payload.phone,
        notes=payload.notes,
    ):
        raise HTTPException(status_code=404, detail="person not found")
    return _to_out(repository.get_person(person_id))


@router.delete("/{person_id}", status_code=204)
def delete_person(person_id: int, confirm: bool = False, repository=Depends(get_repository)):
    """RF-9/RF-10: deletion requires an explicit confirm=true — omitting it
    (or passing false) leaves the person untouched."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="delete requires confirm=true (explicit confirmation, RF-10)",
        )
    if not repository.delete_person(person_id):
        raise HTTPException(status_code=404, detail="person not found")
    return Response(status_code=204)


# -- guided enrollment sessions (RF-1, RF-2, RF-4, RF-5, RF-6, RF-7, RF-8) ---


def _new_enrollment_session(pipeline):
    detector = pipeline.detector
    embedder = pipeline.embedder
    if detector is None or embedder is None:
        # cv2/onnxruntime missing, or the pipeline's worker thread hasn't
        # finished starting up yet -- see vision/pipeline.py's _run().
        raise HTTPException(
            status_code=503, detail="face recognition stack unavailable"
        )
    return EnrollmentSession(detector, embedder, config=pipeline.config.recognition)


@router.post("/enroll", status_code=201)
def start_enrollment(
    person_id: Optional[int] = None,
    pipeline=Depends(get_pipeline),
    repository=Depends(get_repository),
    sessions=Depends(get_enrollment_sessions),
):
    """Starts a guided capture session. Pass `person_id` to re-capture an
    existing person's photos (RF-8); omit it for a brand new alta."""
    if person_id is not None and repository.get_person(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")

    session_id = uuid.uuid4().hex
    sessions[session_id] = {
        "session": _new_enrollment_session(pipeline),
        "person_id": person_id,
    }
    return {"session_id": session_id, "next_pose": "front"}


@router.post("/enroll/{session_id}/photo")
async def enroll_photo(
    session_id: str, photo: UploadFile, sessions=Depends(get_enrollment_sessions)
):
    """Submits the photo for the session's current pose. Rejected photos
    (no face / more than one face) don't advance the session -- the caller
    retakes the same pose."""
    entry = sessions.get(session_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="enrollment session not found")

    image_bytes = await photo.read()
    frame = decode_image(image_bytes)

    try:
        pose = entry["session"].capture(frame, photo_bytes=image_bytes)
    except NoFaceDetected:
        raise HTTPException(status_code=422, detail="no se detectó un rostro en la foto")
    except MultipleFacesDetected:
        raise HTTPException(
            status_code=422, detail="se detectó más de un rostro en la foto"
        )

    return {
        "pose": pose,
        "next_pose": entry["session"].next_pose,
        "is_complete": entry["session"].is_complete,
    }


@router.delete("/enroll/{session_id}", status_code=204)
def cancel_enrollment(session_id: str, sessions=Depends(get_enrollment_sessions)):
    """RF-6/RF-8: abandoning or explicitly cancelling a session leaves no
    trace -- nothing was ever persisted, so this just discards the session."""
    entry = sessions.pop(session_id, None)
    if entry is not None:
        entry["session"].cancel()
    return Response(status_code=204)


@router.post("/enroll/{session_id}/finalize", response_model=PersonOut, status_code=201)
def finalize_enrollment(
    session_id: str,
    payload: PersonIn,
    repository=Depends(get_repository),
    sessions=Depends(get_enrollment_sessions),
):
    entry = sessions.get(session_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="enrollment session not found")

    try:
        captures = entry["session"].finalize()
    except SessionIncomplete:
        raise HTTPException(
            status_code=422, detail="faltan fotos: se requieren las 3 poses"
        )
    except InconsistentPhotos:
        raise HTTPException(
            status_code=422, detail="las 3 fotos no parecen ser la misma persona"
        )

    person_id = entry["person_id"]
    is_new_person = person_id is None

    # RF-7: duplicate check only applies to a brand new alta -- editing an
    # existing person's own photos must not flag itself as a duplicate.
    if is_new_person and repository.existe_duplicado(payload.name, payload.phone):
        sessions.pop(session_id, None)
        raise HTTPException(
            status_code=409,
            detail="ya existe una persona registrada con ese nombre o teléfono",
        )

    if is_new_person:
        person_id = repository.add_person(
            payload.name, payload.age, payload.email, payload.phone, payload.notes
        )
    else:
        repository.update_person(
            person_id,
            name=payload.name,
            age=payload.age,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
        repository.clear_embeddings(person_id)

    for pose, embedding, photo_bytes in captures:
        photo_path = (
            _save_photo(repository, person_id, photo_bytes) if photo_bytes else None
        )
        repository.add_embedding(person_id, embedding, photo_path, pose=pose)

    sessions.pop(session_id, None)
    return _to_out(repository.get_person(person_id))


def _save_photo(repository, person_id, image_bytes):
    photos_dir = os.path.join(repository.config.photos_dir, str(person_id))
    os.makedirs(photos_dir, exist_ok=True)
    filename = "%d_%s.jpg" % (int(time.time()), uuid.uuid4().hex[:8])
    path = os.path.join(photos_dir, filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path
