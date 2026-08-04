"""Database-backed integration tests for label HTTP endpoints under projects."""

from collections.abc import Generator
from uuid import uuid4

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


def get_token(client: TestClient, email: str = "owner@test.com") -> str:
    """Helper to register and login a user."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": "password123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


def setup_workspace_and_project(client: TestClient, token: str) -> str:
    """Create a workspace and a project, return project ID."""
    headers = {"Authorization": f"Bearer {token}"}
    ws_resp = client.post("/api/v1/workspaces", json={"name": "WS"}, headers=headers)
    ws_id = ws_resp.json()["id"]
    
    p_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Proj"},
        headers=headers,
    )
    return p_resp.json()["id"]


def test_label_crud_happy_path(client: TestClient) -> None:
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    project_id = setup_workspace_and_project(client, token)
    base_path = f"/api/v1/projects/{project_id}/labels"

    # Create
    created_response = client.post(base_path, json={"name": "Backend", "color": "#1a73e8"}, headers=headers)
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["name"] == "Backend"

    # List
    listed_response = client.get(base_path, headers=headers)
    assert listed_response.status_code == 200
    assert listed_response.json() == [created]

    # Get
    label_path = f"{base_path}/{created['id']}"
    fetched = client.get(label_path, headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == created

    # Update
    updated_response = client.patch(label_path, json={"name": "Platform"}, headers=headers)
    assert updated_response.status_code == 200
    updated = updated_response.json()
    assert updated["name"] == "Platform"

    # Delete
    deleted = client.delete(label_path, headers=headers)
    assert deleted.status_code == 204

    # List empty
    assert client.get(base_path, headers=headers).json() == []


def test_label_requires_auth(client: TestClient) -> None:
    project_id = uuid4()
    resp = client.post(f"/api/v1/projects/{project_id}/labels", json={"name": "X", "color": "#000000"})
    assert resp.status_code == 401


def test_label_project_not_found(client: TestClient) -> None:
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"/api/v1/projects/{uuid4()}/labels", json={"name": "X", "color": "#000000"}, headers=headers)
    assert resp.status_code == 404
