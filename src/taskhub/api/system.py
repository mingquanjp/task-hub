"""System endpoints that are not business resources."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Response returned when the application is reachable."""

    status: Literal["ok"] = "ok"


@router.get("/health", response_model=HealthResponse, summary="Application health check")
async def health_check() -> HealthResponse:
    """Confirm that the ASGI application can serve requests."""
    return HealthResponse()
