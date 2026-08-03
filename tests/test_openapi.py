"""Tests for OpenAPI configuration and metadata."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings


@pytest.fixture
def client(
    database_url: str,
    security_settings: SecuritySettings,
) -> Generator[TestClient, None, None]:
    app = create_app(database_url=database_url, security_settings=security_settings)
    with TestClient(app) as test_client:
        yield test_client


def test_openapi_schema_contains_bearer_auth(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    # Verify Bearer scheme is registered in components
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["type"] == "http"
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"
    assert security_schemes["HTTPBearer"]["bearerFormat"] == "JWT"


def test_openapi_public_endpoints_have_no_security(client: TestClient) -> None:
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema.get("paths", {})

    public_endpoints = [
        ("/api/v1/auth/register", "post"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/refresh", "post"),
    ]

    for path, method in public_endpoints:
        endpoint = paths.get(path, {}).get(method, {})
        # Should not have security or should have empty security requirements
        # (or not require HTTPBearer)
        security = endpoint.get("security", [])
        assert not any("HTTPBearer" in req for req in security), f"{path} {method} should be public"


def test_openapi_protected_endpoints_have_security(client: TestClient) -> None:
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema.get("paths", {})

    protected_endpoints = [
        ("/api/v1/auth/logout", "post"),
        ("/api/v1/users/me", "get"),
        ("/api/v1/users/me", "patch"),
        ("/api/v1/users/me/change-password", "post"),
    ]

    for path, method in protected_endpoints:
        endpoint = paths.get(path, {}).get(method, {})
        security = endpoint.get("security", [])
        assert any("HTTPBearer" in req for req in security), f"{path} {method} should be protected"


def test_openapi_endpoints_have_error_schemas(client: TestClient) -> None:
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema.get("paths", {})

    # Just spot-check that ErrorResponse is used
    login_responses = paths["/api/v1/auth/login"]["post"]["responses"]
    assert "401" in login_responses

    # Check that it uses the ErrorResponse schema reference
    content = login_responses["401"].get("content", {}).get("application/json", {})
    ref = content.get("schema", {}).get("$ref", "")
    assert "ErrorResponse" in ref
