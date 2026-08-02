"""Integration tests for register/login/refresh/logout HTTP flow."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings


@pytest.fixture
def auth_client(
    database_url: str,
    security_settings: SecuritySettings,
) -> Generator[TestClient, None, None]:
    app = create_app(database_url=database_url, security_settings=security_settings)
    with TestClient(app) as client:
        yield client


def register_payload(email: str = "user@example.com") -> dict[str, str]:
    return {"email": email, "full_name": "Test User", "password": "password123"}


def test_register_login_refresh_and_logout_flow(auth_client: TestClient) -> None:
    register = auth_client.post("/api/v1/auth/register", json=register_payload())
    assert register.status_code == 201
    assert "hashed_password" not in register.json()

    duplicate = auth_client.post("/api/v1/auth/register", json=register_payload("USER@example.com"))
    assert duplicate.status_code == 409

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "USER@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 900

    refresh = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    rotated = refresh.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    reused = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reused.status_code == 401

    logout = auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert logout.status_code == 204
    assert logout.content == b""

    refresh_after_logout = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401

    invalid_logout = auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert invalid_logout.status_code == 204


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/auth/register", {"email": "bad", "full_name": "User", "password": "password123"}),
        ("/api/v1/auth/register", register_payload() | {"password": "short"}),
        ("/api/v1/auth/login", {"email": "bad", "password": "password123"}),
        ("/api/v1/auth/refresh", {}),
    ],
)
def test_auth_validation_returns_422(
    auth_client: TestClient,
    path: str,
    payload: dict[str, str],
) -> None:
    assert auth_client.post(path, json=payload).status_code == 422


def test_invalid_login_returns_generic_401(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_refresh_rejects_forged_access_and_malformed_tokens(auth_client: TestClient) -> None:
    auth_client.post("/api/v1/auth/register", json=register_payload())
    tokens = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    ).json()

    forged = tokens["refresh_token"][:-1] + ("A" if tokens["refresh_token"][-1] != "A" else "B")
    assert (
        auth_client.post("/api/v1/auth/refresh", json={"refresh_token": forged}).status_code == 401
    )
    assert (
        auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        ).status_code
        == 401
    )
    assert (
        auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-jwt"},
        ).status_code
        == 401
    )
