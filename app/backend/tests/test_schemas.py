import pytest
from pydantic import ValidationError

from app.backend.schemas import PersonIn, PersonUpdate


def _person(**overrides):
    data = dict(name="Ada Lovelace", age=30, email="ada@example.com", phone="+1 555 0100")
    data.update(overrides)
    return data


def test_person_in_accepts_valid_values():
    person = PersonIn(**_person())
    assert person.email == "ada@example.com"
    assert person.phone == "+1 555 0100"


def test_person_in_accepts_age_without_range_restriction():
    assert PersonIn(**_person(age=0)).age == 0
    assert PersonIn(**_person(age=130)).age == 130
    assert PersonIn(**_person(age=-1)).age == -1


def test_person_in_rejects_email_without_at_sign():
    with pytest.raises(ValidationError):
        PersonIn(**_person(email="not-an-email"))


def test_person_in_rejects_phone_with_letters():
    with pytest.raises(ValidationError):
        PersonIn(**_person(phone="555-CALL-NOW"))


def test_person_update_allows_omitted_fields():
    update = PersonUpdate(notes="updated notes")
    assert update.email is None
    assert update.phone is None


def test_person_update_validates_email_and_phone_when_present():
    with pytest.raises(ValidationError):
        PersonUpdate(email="bad-email")
    with pytest.raises(ValidationError):
        PersonUpdate(phone="abc")
    assert PersonUpdate(email="new@example.com").email == "new@example.com"
