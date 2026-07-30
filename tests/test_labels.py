"""Tests for label domain and schema contracts."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.schemas import LabelCreate, LabelResponse, LabelUpdate


def test_label_is_a_plain_python_domain_entity() -> None:
    """The domain entity stores typed values without HTTP or Pydantic behavior."""
    label = Label(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")

    assert label.name == "Backend"
    assert label.color == "#1A73E8"


def test_label_create_validates_and_normalizes_input() -> None:
    """Create data trims names and stores colors in uppercase."""
    payload = LabelCreate(name="  Backend  ", color="#1a73e8")

    assert payload.name == "Backend"
    assert payload.color == "#1A73E8"


@pytest.mark.parametrize(
    ("name", "color"),
    [
        ("", "#1A73E8"),
        (" ", "#1A73E8"),
        ("a" * 51, "#1A73E8"),
        ("Backend", "1A73E8"),
        ("Backend", "#1A73E"),
        ("Backend", "#1A73E8FF"),
    ],
)
def test_label_create_rejects_invalid_fields(name: str, color: str) -> None:
    """Names and colors must follow the Label API contract."""
    with pytest.raises(ValidationError):
        LabelCreate(name=name, color=color)


def test_label_update_tracks_only_provided_fields() -> None:
    """PATCH data keeps omitted fields distinct from fields supplied by the client."""
    payload = LabelUpdate(color="#ff9800")

    assert payload.model_fields_set == {"color"}
    assert payload.model_dump(exclude_unset=True) == {"color": "#FF9800"}


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": None}, {"color": None}],
)
def test_label_update_rejects_empty_or_null_payloads(payload: dict[str, object]) -> None:
    """PATCH requires one concrete value to change."""
    with pytest.raises(ValidationError):
        LabelUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [{"name": " "}, {"color": "orange"}],
)
def test_label_update_rejects_invalid_provided_fields(payload: dict[str, object]) -> None:
    """PATCH validates each concrete field with the same contract as creation."""
    with pytest.raises(ValidationError):
        LabelUpdate.model_validate(payload)


def test_label_response_parses_uuid_fields() -> None:
    """Response data exposes IDs as UUID values."""
    label_id = uuid4()
    project_id = uuid4()
    response = LabelResponse.model_validate(
        {
            "id": str(label_id),
            "project_id": str(project_id),
            "name": "  Backend  ",
            "color": "#1a73e8",
        }
    )

    assert response.id == UUID(str(label_id))
    assert response.project_id == UUID(str(project_id))
    assert response.name == "Backend"
    assert response.color == "#1A73E8"


def test_label_response_reads_from_a_domain_entity() -> None:
    """Response schemas can serialize the domain entity without HTTP coupling."""
    label = Label(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")

    response = LabelResponse.model_validate(label)

    assert response.id == label.id
    assert response.project_id == label.project_id
