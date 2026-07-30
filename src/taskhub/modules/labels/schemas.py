"""Pydantic request and response schemas for labels."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

_HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
_HexColor = Annotated[str, Field(pattern=_HEX_COLOR_PATTERN)]


class LabelCreate(BaseModel):
    """Data required to create a label."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    color: str = Field(pattern=_HEX_COLOR_PATTERN)

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str) -> str:
        """Store hex colors in a consistent uppercase representation."""
        return value.upper()


class LabelUpdate(BaseModel):
    """Fields that may be changed by a partial label update."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | SkipJsonSchema[None] = Field(default=None, min_length=1, max_length=50)
    color: _HexColor | SkipJsonSchema[None] = None

    @field_validator("name", "color", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        """Reject explicit null while allowing omitted fields in a PATCH payload."""
        if value is None:
            raise ValueError("field cannot be null")
        return value

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str | None) -> str | None:
        """Store provided hex colors in a consistent uppercase representation."""
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_partial_update(self) -> Self:
        """Require at least one field for an update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for an update")
        return self


class LabelResponse(BaseModel):
    """Public representation of a label."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: UUID
    project_id: UUID
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(pattern=_HEX_COLOR_PATTERN)

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str) -> str:
        """Expose hex colors in the canonical uppercase representation."""
        return value.upper()
