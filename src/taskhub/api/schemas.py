"""Standardized API response schemas."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    request_id: str = Field(description="Unique identifier for request correlation")


class PaginatedResponse[T](BaseModel):
    """Standardized paginated response payload."""

    items: list[T] = Field(description="List of items in the current page")
    total: int = Field(description="Total number of items matching the query")
    page: int = Field(description="Current page number")
    limit: int = Field(description="Number of items per page")
