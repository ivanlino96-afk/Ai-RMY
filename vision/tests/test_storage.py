import os

import numpy as np
import pytest

from vision.config import StorageConfig
from vision.storage.repository import FaceRepository


@pytest.fixture
def repo(tmp_path):
    config = StorageConfig(
        db_path=str(tmp_path / "faces.db"), photos_dir=str(tmp_path / "faces")
    )
    repository = FaceRepository(config)
    yield repository
    repository.close()


def _add(repo, name, age=30, email="person@example.com", phone="+1000", notes=""):
    return repo.add_person(name, age, email, phone, notes=notes)


def test_add_and_get_person(repo):
    person_id = _add(repo, "Ada Lovelace", age=28, email="ada@example.com", phone="+1111", notes="test subject")
    person = repo.get_person(person_id)
    assert person.name == "Ada Lovelace"
    assert person.age == 28
    assert person.email == "ada@example.com"
    assert person.phone == "+1111"
    assert person.notes == "test subject"


def test_list_people_sorted_by_name(repo):
    _add(repo, "Zoe")
    _add(repo, "Ada")
    names = [p.name for p in repo.list_people()]
    assert names == ["Ada", "Zoe"]


def test_update_person(repo):
    person_id = _add(repo, "Original Name")
    assert repo.update_person(person_id, name="New Name")
    assert repo.get_person(person_id).name == "New Name"


def test_update_person_age_email_phone(repo):
    person_id = _add(repo, "Someone", age=20, email="old@example.com", phone="+1")
    assert repo.update_person(person_id, age=21, email="new@example.com", phone="+2")
    person = repo.get_person(person_id)
    assert person.age == 21
    assert person.email == "new@example.com"
    assert person.phone == "+2"


def test_update_missing_person_returns_false(repo):
    assert repo.update_person(9999, name="Nobody") is False


def test_existe_duplicado_by_normalized_name(repo):
    _add(repo, "Ada Lovelace", phone="+1000")
    assert repo.existe_duplicado("  ADA lovelace  ", "+9999") is True


def test_existe_duplicado_by_exact_phone(repo):
    _add(repo, "Ada Lovelace", phone="+1234")
    assert repo.existe_duplicado("Someone Else", "+1234") is True


def test_existe_duplicado_false_for_new_person(repo):
    _add(repo, "Ada Lovelace", phone="+1234")
    assert repo.existe_duplicado("Grace Hopper", "+5678") is False


def test_existe_duplicado_ignores_deleted_person(repo):
    person_id = _add(repo, "Ada Lovelace", phone="+1234")
    repo.delete_person(person_id)
    assert repo.existe_duplicado("Ada Lovelace", "+1234") is False


def test_delete_person_removes_embeddings(repo):
    person_id = _add(repo, "To Delete")
    repo.add_embedding(person_id, np.ones(128, dtype=np.float32))
    assert repo.delete_person(person_id) is True
    assert repo.get_person(person_id) is None
    assert repo.list_embeddings(person_id) == []


def test_delete_person_removes_photo_files(repo):
    person_id = _add(repo, "To Delete")
    photo_dir = os.path.join(repo.config.photos_dir, str(person_id))
    os.makedirs(photo_dir, exist_ok=True)
    photo_path = os.path.join(photo_dir, "front.jpg")
    with open(photo_path, "wb") as f:
        f.write(b"fake-jpeg-bytes")
    repo.add_embedding(person_id, np.ones(128, dtype=np.float32), photo_path=photo_path, pose="front")

    assert repo.delete_person(person_id) is True

    assert not os.path.isdir(photo_dir)


def test_clear_embeddings_removes_rows_and_photos_but_keeps_person(repo):
    person_id = _add(repo, "Re-capture Me")
    photo_dir = os.path.join(repo.config.photos_dir, str(person_id))
    os.makedirs(photo_dir, exist_ok=True)
    photo_path = os.path.join(photo_dir, "front.jpg")
    with open(photo_path, "wb") as f:
        f.write(b"fake-jpeg-bytes")
    repo.add_embedding(person_id, np.ones(128, dtype=np.float32), photo_path=photo_path, pose="front")

    repo.clear_embeddings(person_id)

    assert repo.get_person(person_id) is not None
    assert repo.list_embeddings(person_id) == []
    assert not os.path.isdir(photo_dir)


def test_embedding_stores_pose(repo):
    person_id = _add(repo, "Someone")
    repo.add_embedding(person_id, np.ones(128, dtype=np.float32), pose="left")
    row = repo._conn.execute(
        "SELECT pose FROM embeddings WHERE person_id = ?", (person_id,)
    ).fetchone()
    assert row[0] == "left"


def test_find_best_match_returns_closest_person_above_threshold(repo):
    person_id = _add(repo, "Match Me")
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    repo.add_embedding(person_id, vector)

    match = repo.find_best_match(vector, threshold=0.9)
    assert match is not None
    assert match.person_id == person_id
    assert match.name == "Match Me"
    assert match.score == pytest.approx(1.0)


def test_find_best_match_below_threshold_returns_none(repo):
    person_id = _add(repo, "Someone")
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    repo.add_embedding(person_id, vector)

    orthogonal = np.zeros(128, dtype=np.float32)
    orthogonal[1] = 1.0
    assert repo.find_best_match(orthogonal, threshold=0.5) is None


def test_find_best_match_with_no_embeddings_returns_none(repo):
    assert repo.find_best_match(np.ones(128, dtype=np.float32), threshold=0.1) is None


def test_find_all_matches_returns_all_above_threshold_sorted_desc(repo):
    query = np.zeros(128, dtype=np.float32)
    query[0] = 1.0

    best_id = _add(repo, "Best Match", phone="+1")
    best_vector = np.zeros(128, dtype=np.float32)
    best_vector[0] = 1.0
    repo.add_embedding(best_id, best_vector)

    second_id = _add(repo, "Second Match", phone="+2")
    second_vector = np.zeros(128, dtype=np.float32)
    second_vector[0] = 0.95
    second_vector[1] = 0.05
    repo.add_embedding(second_id, second_vector)

    below_id = _add(repo, "Below Threshold", phone="+3")
    below_vector = np.zeros(128, dtype=np.float32)
    below_vector[1] = 1.0
    repo.add_embedding(below_id, below_vector)

    matches = repo.find_all_matches(query, threshold=0.5)

    assert [m.person_id for m in matches] == [best_id, second_id]
    assert matches[0].score >= matches[1].score


def test_find_all_matches_empty_when_no_people_registered(repo):
    query = np.ones(128, dtype=np.float32)
    assert repo.find_all_matches(query, threshold=0.5) == []


def test_find_all_matches_no_longer_matches_deleted_person(repo):
    """T17: after a delete, the next recognition cycle must not find this
    person -- deletion removes the embeddings a live match would score
    against, not just the people row."""
    person_id = _add(repo, "Deleted Person", phone="+9000")
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    repo.add_embedding(person_id, vector)
    assert repo.find_all_matches(vector, threshold=0.9) != []

    repo.delete_person(person_id)

    assert repo.find_all_matches(vector, threshold=0.9) == []
