"""Standardized API response schemas."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    request_id: str = Field(description="Unique identifier for request correlation")
