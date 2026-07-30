"""Integration tests for the FastAPI application core."""

from fastapi.testclient import TestClient

from taskhub.api.v1.router import router as api_v1_router
from taskhub.application import create_app
from taskhub.modules.labels.router import router as labels_router


def test_lifespan_manages_application_state() -> None:
    """Startup and shutdown update application-scoped lifecycle state."""
    app = create_app()

    with TestClient(app):
        assert app.state.core_started is True

    assert app.state.core_started is False


def test_health_check_returns_ok() -> None:
    """The health endpoint is available while the application is running."""
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_documentation_endpoints_are_available() -> None:
    """FastAPI serves OpenAPI, Swagger UI, and ReDoc."""
    with TestClient(create_app()) as client:
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


def test_router_composition_uses_the_expected_version_and_resource_prefixes() -> None:
    """Version and feature routers keep their path and OpenAPI metadata local."""
    assert api_v1_router.prefix == "/api/v1"
    assert labels_router.prefix == "/projects/{project_id}/labels"
    assert labels_router.tags == ["labels"]
