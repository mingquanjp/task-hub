"""FastAPI application factory and application lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from taskhub.api.errors import (
    domain_error_handler,
    internal_error_handler,
    validation_error_handler,
)
from taskhub.api.middlewares import RequestContextMiddleware, RequestLoggingMiddleware
from taskhub.api.router import router as api_router
from taskhub.core.config import SecuritySettings, get_security_settings, get_settings
from taskhub.core.exceptions import DomainError
from taskhub.infrastructure.database.session import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-scoped resources for the ASGI lifespan."""
    database_url = app.state.database_url or get_settings().database_url
    security_settings = app.state.security_settings or get_security_settings()
    database = Database(database_url)
    app.state.engine = database.engine
    app.state.session_factory = database.session_factory
    app.state.security_settings = security_settings
    app.state.core_started = True
    try:
        yield
    finally:
        app.state.core_started = False
        await database.dispose()


def create_app(
    *,
    database_url: str | None = None,
    security_settings: SecuritySettings | None = None,
) -> FastAPI:
    """Create and configure the TaskHub FastAPI application."""
    app = FastAPI(
        title="TaskHub API",
        description="Task management API for collaborative workspaces.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.database_url = database_url
    app.state.security_settings = security_settings

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, internal_error_handler)

    app.include_router(api_router)
    return app
