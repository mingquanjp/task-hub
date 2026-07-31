"""FastAPI application factory and application lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from taskhub.api.router import router as api_router
from taskhub.core.config import get_settings
from taskhub.infrastructure.database.session import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-scoped resources for the ASGI lifespan."""
    database_url = app.state.database_url or get_settings().database_url
    database = Database(database_url)
    app.state.engine = database.engine
    app.state.session_factory = database.session_factory
    app.state.core_started = True
    try:
        yield
    finally:
        app.state.core_started = False
        await database.dispose()


def create_app(*, database_url: str | None = None) -> FastAPI:
    """Create and configure the TaskHub FastAPI application."""
    app = FastAPI(
        title="TaskHub API",
        description="Task management API for collaborative workspaces.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database_url = database_url
    app.include_router(api_router)
    return app
