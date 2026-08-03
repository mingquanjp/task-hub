"""Integration tests for users HTTP flow."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings


@pytest.fixture
def api_client(
    database_url: str,
    security_settings: SecuritySettings,
) -> Generator[TestClient, None, None]:
    app = create_app(database_url=database_url, security_settings=security_settings)
    with TestClient(app) as client:
        yield client


def test_users_api_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/users/me").status_code == 401
    assert api_client.patch("/api/v1/users/me", json={"full_name": "Name"}).status_code == 401
    assert (
        api_client.post(
            "/api/v1/users/me/change-password", json={"current_password": "p", "new_password": "n"}
        ).status_code
        == 401
    )


def test_users_api_flow(api_client: TestClient) -> None:
    # 1. Register and Login
    register = api_client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "full_name": "Test User", "password": "password123"},
    )
    assert register.status_code == 201

    login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Get profile
    profile = api_client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 200
    data = profile.json()
    assert data["email"] == "user@example.com"
    assert data["full_name"] == "Test User"
    assert "hashed_password" not in data

    # 3. Update profile
    update = api_client.patch(
        "/api/v1/users/me",
        json={"full_name": "New Name", "email": "NEW@EXAMPLE.COM"},
        headers=headers,
    )
    assert update.status_code == 200
    updated_data = update.json()
    assert updated_data["full_name"] == "New Name"
    assert updated_data["email"] == "new@example.com"

    # 4. Check empty update body returns 422
    empty_update = api_client.patch("/api/v1/users/me", json={}, headers=headers)
    assert empty_update.status_code == 422

    # Check explicit null returns 422
    null_update = api_client.patch("/api/v1/users/me", json={"email": None}, headers=headers)
    assert null_update.status_code == 422
    null_name_update = api_client.patch(
        "/api/v1/users/me", json={"full_name": None}, headers=headers
    )
    assert null_name_update.status_code == 422

    # 5. Check duplicate email returns 409
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "full_name": "Other", "password": "password123"},
    )
    duplicate_update = api_client.patch(
        "/api/v1/users/me",
        json={"email": "other@example.com"},
        headers=headers,
    )
    assert duplicate_update.status_code == 409

    # 6. Change password incorrectly
    wrong_pwd = api_client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "wrong-password", "new_password": "new-password123"},
        headers=headers,
    )
    assert wrong_pwd.status_code == 400

    # 7. Change password successfully
    change_pwd = api_client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "password123", "new_password": "new-password123"},
        headers=headers,
    )
    assert change_pwd.status_code == 204

    # 8. Check refresh tokens are revoked
    refresh = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh.status_code == 401

    # 9. Check can login with new password
    new_login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": "new-password123"},
    )
    assert new_login.status_code == 200


def test_users_api_rejects_refresh_token(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "full_name": "Test User", "password": "password123"},
    )
    login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}

    profile = api_client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 401
    assert profile.headers.get("WWW-Authenticate") == "Bearer"
