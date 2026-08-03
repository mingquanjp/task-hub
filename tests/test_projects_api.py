"""Integration tests for project API endpoints."""

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


def create_workspace(client: TestClient, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    ws_resp = client.post("/api/v1/workspaces", json={"name": "WS"}, headers=headers)
    return ws_resp.json()["id"]


def test_project_crud(client: TestClient) -> None:
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    ws_id = create_workspace(client, token)

    # 1. Create project
    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "New Project"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    project = create_resp.json()
    assert project["name"] == "New Project"
    assert project["workspace_id"] == ws_id
    assert project["status"] == "ACTIVE"
    project_id = project["id"]

    # 2. Get project
    get_resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "New Project"

    # 3. List projects
    list_resp = client.get(f"/api/v1/workspaces/{ws_id}/projects", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 4. Update project
    update_resp = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated Project", "description": "New desc"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Project"
    assert update_resp.json()["description"] == "New desc"

    # 5. Archive project
    archive_resp = client.post(f"/api/v1/projects/{project_id}/archive", headers=headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "ARCHIVED"

    # 6. Delete project
    delete_resp = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Verify deleted
    assert client.get(f"/api/v1/projects/{project_id}", headers=headers).status_code == 404


def test_project_authorization(client: TestClient) -> None:
    owner_token = get_token(client, "owner@test.com")
    viewer_token = get_token(client, "viewer@test.com")
    
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    
    ws_id = create_workspace(client, owner_token)
    
    viewer_id = client.get("/api/v1/users/me", headers=viewer_headers).json()["id"]
    
    # Add viewer to workspace
    client.post(f"/api/v1/workspaces/{ws_id}/members", json={"user_id": viewer_id, "role": "VIEWER"}, headers=owner_headers)
    
    # Owner can create project
    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "New Project"},
        headers=owner_headers,
    )
    project_id = create_resp.json()["id"]

    # Viewer cannot create project
    assert client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Viewer Project"},
        headers=viewer_headers,
    ).status_code == 403

    # Viewer can get project
    assert client.get(f"/api/v1/projects/{project_id}", headers=viewer_headers).status_code == 200

    # Viewer cannot update project
    assert client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Viewer Update"},
        headers=viewer_headers,
    ).status_code == 403

    # Viewer cannot archive project
    assert client.post(
        f"/api/v1/projects/{project_id}/archive",
        headers=viewer_headers,
    ).status_code == 403

    # Viewer cannot delete project
    assert client.delete(
        f"/api/v1/projects/{project_id}",
        headers=viewer_headers,
    ).status_code == 403
