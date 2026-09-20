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


def test_add_and_get_person(repo):
    person_id = repo.add_person("Ada Lovelace", notes="test subject")
    person = repo.get_person(person_id)
    assert person.name == "Ada Lovelace"
    assert person.notes == "test subject"


def test_list_people_sorted_by_name(repo):
    repo.add_person("Zoe")
    repo.add_person("Ada")
    names = [p.name for p in repo.list_people()]
    assert names == ["Ada", "Zoe"]


def test_update_person(repo):
    person_id = repo.add_person("Original Name")
    assert repo.update_person(person_id, name="New Name")
    assert repo.get_person(person_id).name == "New Name"


def test_update_missing_person_returns_false(repo):
    assert repo.update_person(9999, name="Nobody") is False


def test_delete_person_removes_embeddings(repo):
    person_id = repo.add_person("To Delete")
    repo.add_embedding(person_id, np.ones(128, dtype=np.float32))
    assert repo.delete_person(person_id) is True
    assert repo.get_person(person_id) is None
    assert repo.list_embeddings(person_id) == []


def test_find_best_match_returns_closest_person_above_threshold(repo):
    person_id = repo.add_person("Match Me")
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    repo.add_embedding(person_id, vector)

    match = repo.find_best_match(vector, threshold=0.9)
    assert match is not None
    assert match.person_id == person_id
    assert match.name == "Match Me"
    assert match.score == pytest.approx(1.0)


def test_find_best_match_below_threshold_returns_none(repo):
    person_id = repo.add_person("Someone")
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    repo.add_embedding(person_id, vector)

    orthogonal = np.zeros(128, dtype=np.float32)
    orthogonal[1] = 1.0
    assert repo.find_best_match(orthogonal, threshold=0.5) is None


def test_find_best_match_with_no_embeddings_returns_none(repo):
    assert repo.find_best_match(np.ones(128, dtype=np.float32), threshold=0.1) is None
