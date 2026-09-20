import os
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from app.backend.dependencies import get_repository
from app.backend.schemas import PersonOut, PersonUpdate
from vision.enroll import NoFaceDetected, embed_face_from_image_bytes

router = APIRouter(prefix="/api/people", tags=["people"])


def _to_out(person):
    return PersonOut(
        id=person.id, name=person.name, notes=person.notes, created_at=person.created_at
    )


@router.get("", response_model=List[PersonOut])
def list_people(repository=Depends(get_repository)):
    return [_to_out(p) for p in repository.list_people()]


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(
    photo: UploadFile,
    name: str = Form(...),
    notes: str = Form(""),
    repository=Depends(get_repository),
):
    image_bytes = await photo.read()
    embedding = _embed_or_503(image_bytes)

    person_id = repository.add_person(name, notes)
    photo_path = _save_photo(repository, person_id, image_bytes)
    repository.add_embedding(person_id, embedding, photo_path)
    return _to_out(repository.get_person(person_id))


@router.get("/{person_id}/photo")
def get_person_photo(person_id: int, repository=Depends(get_repository)):
    photo_path = repository.latest_photo_path(person_id)
    if photo_path is None or not os.path.isfile(photo_path):
        raise HTTPException(status_code=404, detail="no photo for this person")
    return FileResponse(photo_path, media_type="image/jpeg")


@router.post("/{person_id}/photos", status_code=201)
async def add_photo(person_id: int, photo: UploadFile, repository=Depends(get_repository)):
    if repository.get_person(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")

    image_bytes = await photo.read()
    embedding = _embed_or_503(image_bytes)

    photo_path = _save_photo(repository, person_id, image_bytes)
    repository.add_embedding(person_id, embedding, photo_path)
    return {"ok": True}


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(person_id: int, payload: PersonUpdate, repository=Depends(get_repository)):
    if not repository.update_person(person_id, name=payload.name, notes=payload.notes):
        raise HTTPException(status_code=404, detail="person not found")
    return _to_out(repository.get_person(person_id))


@router.delete("/{person_id}", status_code=204)
def delete_person(person_id: int, repository=Depends(get_repository)):
    if not repository.delete_person(person_id):
        raise HTTPException(status_code=404, detail="person not found")
    return Response(status_code=204)


def _embed_or_503(image_bytes):
    try:
        return embed_face_from_image_bytes(image_bytes)
    except NoFaceDetected:
        raise HTTPException(status_code=422, detail="no face detected in photo")
    except (ImportError, RuntimeError) as exc:
        # cv2/onnxruntime missing or the JetPack 4.6 OpenCV build lacks
        # FaceDetectorYN — see vision/detection/yunet.py and
        # AGENTS.md's Python 3.6 compatibility note. Enrollment can't work
        # without the CV stack, but this should read as a clear 503, not a
        # raw stack trace.
        raise HTTPException(status_code=503, detail="face recognition stack unavailable: %s" % exc)


def _save_photo(repository, person_id, image_bytes):
    photos_dir = os.path.join(repository.config.photos_dir, str(person_id))
    os.makedirs(photos_dir, exist_ok=True)
    filename = "%d_%s.jpg" % (int(time.time()), uuid.uuid4().hex[:8])
    path = os.path.join(photos_dir, filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path
