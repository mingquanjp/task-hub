"""Integration tests for the FastAPI application core."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from taskhub.api.v1.router import router as api_v1_router
from taskhub.application import create_app
from taskhub.core.config import SecuritySettings
from taskhub.infrastructure.database.session import Database
from taskhub.modules.labels.router import router as labels_router


def test_lifespan_manages_application_state(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    """Startup and shutdown update application-scoped lifecycle state."""
    app = create_app(database_url=database_url, security_settings=security_settings)

    with TestClient(app):
        assert app.state.core_started is True
        assert app.state.engine.url.get_backend_name() == "sqlite"
        assert app.state.session_factory.kw["expire_on_commit"] is False

    assert app.state.core_started is False


def test_health_check_returns_ok(database_url: str, security_settings: SecuritySettings) -> None:
    """The health endpoint is available while the application is running."""
    with TestClient(
        create_app(database_url=database_url, security_settings=security_settings)
    ) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_documentation_endpoints_are_available(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    """FastAPI serves OpenAPI, Swagger UI, and ReDoc."""
    with TestClient(
        create_app(database_url=database_url, security_settings=security_settings)
    ) as client:
        openapi_response = client.get("/openapi.json")
        docs_response = client.get("/docs")
        redoc_response = client.get("/redoc")

    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"] == {
        "title": "TaskHub API",
        "description": "Task management API for collaborative workspaces.",
        "version": "0.1.0",
    }
    assert "/health" in openapi_response.json()["paths"]
    auth_paths = openapi_response.json()["paths"]
    assert {"post"} == set(auth_paths["/api/v1/auth/register"])
    assert auth_paths["/api/v1/auth/register"]["post"]["responses"].get("409") is not None
    assert auth_paths["/api/v1/auth/login"]["post"]["responses"].get("401") is not None
    assert auth_paths["/api/v1/auth/refresh"]["post"]["responses"].get("401") is not None
    assert auth_paths["/api/v1/auth/logout"]["post"]["responses"].get("204") is not None
    label_path = "/api/v1/projects/{project_id}/labels"
    label_item_path = f"{label_path}/{{label_id}}"
    assert set(openapi_response.json()["paths"][label_path]) == {"get", "post"}
    assert set(openapi_response.json()["paths"][label_item_path]) == {"get", "patch", "delete"}
    assert openapi_response.json()["paths"][label_path]["post"]["responses"].get("201") is not None
    delete_responses = openapi_response.json()["paths"][label_item_path]["delete"]["responses"]
    assert delete_responses.get("204") is not None
    assert delete_responses.get("404") == {"description": "Label not found"}
    label_update_schema = openapi_response.json()["components"]["schemas"]["LabelUpdate"]
    assert label_update_schema["properties"]["name"]["type"] == "string"
    assert label_update_schema["properties"]["color"]["type"] == "string"
    assert label_update_schema["properties"]["color"]["pattern"] == "^#[0-9A-Fa-f]{6}$"
    assert docs_response.status_code == 200
    assert redoc_response.status_code == 200


def test_lifespan_fails_before_database_startup_without_security_settings(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_security_settings() -> SecuritySettings:
        raise RuntimeError("JWT_SECRET_KEY is required")

    monkeypatch.setattr("taskhub.application.get_security_settings", missing_security_settings)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        with TestClient(create_app(database_url=database_url)):
            pass


def test_router_composition_uses_the_expected_version_and_resource_prefixes() -> None:
    """Version and feature routers keep their path and OpenAPI metadata local."""
    assert api_v1_router.prefix == "/api/v1"
    assert labels_router.prefix == "/projects/{project_id}/labels"
    assert labels_router.tags == ["labels"]


def test_lifespan_disposes_the_database_engine(
    database_url: str,
    security_settings: SecuritySettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispose = AsyncMock()
    monkeypatch.setattr(Database, "dispose", dispose)

    with TestClient(create_app(database_url=database_url, security_settings=security_settings)):
        pass

    dispose.assert_awaited_once()
