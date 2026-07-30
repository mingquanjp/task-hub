"""FastAPI application factory and application lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from taskhub.api.router import router as api_router
from taskhub.modules.labels.repository import InMemoryLabelRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-scoped resources for the ASGI lifespan."""
    app.state.core_started = True
    try:
        yield
    finally:
        app.state.core_started = False


def create_app() -> FastAPI:
    """Create and configure the TaskHub FastAPI application."""
    app = FastAPI(
        title="TaskHub API",
        description="Task management API for collaborative workspaces.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.label_repository = InMemoryLabelRepository()
    app.include_router(api_router)
    return app
