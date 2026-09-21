from vision.detection.yunet import Detection

_LANDMARKS = ((0.0, 0.0), (10.0, 0.0), (5.0, 5.0), (0.0, 10.0), (10.0, 10.0))
_ADA = {"name": "Ada Lovelace", "age": 30, "email": "ada@example.com", "phone": "+1000"}


class _NoFaceDetector(object):
    def detect(self, frame):
        return []


class _TwoFaceDetector(object):
    def detect(self, frame):
        detection = Detection(bbox=(0.0, 0.0, 20.0, 20.0), landmarks=_LANDMARKS, score=0.99)
        return [detection, detection]


def _start_session(client, person_id=None):
    params = {"person_id": person_id} if person_id is not None else {}
    resp = client.post("/api/people/enroll", params=params)
    assert resp.status_code == 201
    return resp.json()["session_id"]


def _submit_photo(client, session_id):
    return client.post(
        "/api/people/enroll/%s/photo" % session_id,
        files={"photo": ("photo.jpg", b"fake-jpeg-bytes", "image/jpeg")},
    )


def _complete_session(client, person_id=None):
    session_id = _start_session(client, person_id=person_id)
    for _ in range(3):
        resp = _submit_photo(client, session_id)
        assert resp.status_code == 200
    return session_id


def _finalize(client, session_id, **overrides):
    payload = dict(_ADA, **overrides)
    return client.post("/api/people/enroll/%s/finalize" % session_id, json=payload)


# -- T14: guided enrollment session, end to end ------------------------------


def test_enrollment_end_to_end_creates_person(client):
    session_id = _complete_session(client)
    resp = _finalize(client, session_id)

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Ada Lovelace"
    assert body["age"] == 30
    assert body["email"] == "ada@example.com"

    people = client.get("/api/people").json()
    assert any(p["name"] == "Ada Lovelace" for p in people)


def test_cancelled_enrollment_leaves_no_person(client):
    session_id = _start_session(client)
    _submit_photo(client, session_id)

    cancel_resp = client.delete("/api/people/enroll/%s" % session_id)
    assert cancel_resp.status_code == 204

    assert client.get("/api/people").json() == []


def test_photo_with_no_face_is_rejected_and_does_not_advance(client, fake_pipeline):
    fake_pipeline.detector = _NoFaceDetector()
    session_id = _start_session(client)

    resp = _submit_photo(client, session_id)
    assert resp.status_code == 422


def test_photo_with_two_faces_is_rejected(client, fake_pipeline):
    fake_pipeline.detector = _TwoFaceDetector()
    session_id = _start_session(client)

    resp = _submit_photo(client, session_id)
    assert resp.status_code == 422


def test_finalize_before_three_photos_is_rejected(client):
    session_id = _start_session(client)
    _submit_photo(client, session_id)

    resp = _finalize(client, session_id)
    assert resp.status_code == 422


# -- T15: duplicate name/phone rejected on finalize --------------------------


def test_duplicate_phone_rejected_on_finalize(client):
    first_session = _complete_session(client)
    assert _finalize(client, first_session).status_code == 201

    second_session = _complete_session(client)
    resp = _finalize(client, second_session, name="Different Name", email="other@example.com")

    assert resp.status_code == 409
    people = client.get("/api/people").json()
    assert len(people) == 1


# -- T16: editing data vs. re-capturing photos -------------------------------


def test_patch_updates_data_without_touching_photos(client, repository):
    session_id = _complete_session(client)
    person_id = _finalize(client, session_id).json()["id"]
    embeddings_before = repository.list_embeddings(person_id)

    resp = client.patch("/api/people/%d" % person_id, json={"email": "new@example.com"})

    assert resp.status_code == 200
    assert resp.json()["email"] == "new@example.com"
    assert resp.json()["name"] == "Ada Lovelace"
    embeddings_after = repository.list_embeddings(person_id)
    assert len(embeddings_after) == len(embeddings_before)
    assert [pid for pid, _ in embeddings_after] == [pid for pid, _ in embeddings_before]


def test_cancelled_photo_recapture_preserves_existing_data(client, repository):
    session_id = _complete_session(client)
    person_id = _finalize(client, session_id).json()["id"]
    embeddings_before = repository.list_embeddings(person_id)

    recapture_session_id = _start_session(client, person_id=person_id)
    _submit_photo(client, recapture_session_id)
    cancel_resp = client.delete("/api/people/enroll/%s" % recapture_session_id)

    assert cancel_resp.status_code == 204
    people = client.get("/api/people").json()
    assert any(p["id"] == person_id and p["name"] == "Ada Lovelace" for p in people)
    assert len(repository.list_embeddings(person_id)) == len(embeddings_before) == 3


def test_completed_photo_recapture_replaces_embeddings(client, repository):
    session_id = _complete_session(client)
    person_id = _finalize(client, session_id).json()["id"]

    recapture_session_id = _complete_session(client, person_id=person_id)
    resp = client.post(
        "/api/people/enroll/%s/finalize" % recapture_session_id,
        json=_ADA,
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == person_id
    # Old embeddings/photos were cleared and replaced by the new 3, not
    # appended to.
    assert len(repository.list_embeddings(person_id)) == 3


# -- T17: delete requires explicit confirmation ------------------------------


def test_delete_without_confirm_leaves_person_intact(client):
    session_id = _complete_session(client)
    person_id = _finalize(client, session_id).json()["id"]

    resp = client.delete("/api/people/%d" % person_id)

    assert resp.status_code == 400
    people = client.get("/api/people").json()
    assert any(p["id"] == person_id for p in people)


def test_delete_with_confirm_removes_person(client):
    session_id = _complete_session(client)
    person_id = _finalize(client, session_id).json()["id"]

    resp = client.delete("/api/people/%d" % person_id, params={"confirm": "true"})

    assert resp.status_code == 204
    assert client.get("/api/people").json() == []
