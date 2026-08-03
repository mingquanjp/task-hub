"""Integration tests for task API endpoints."""

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


def create_workspace_and_project(client: TestClient, token: str) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    ws_resp = client.post("/api/v1/workspaces", json={"name": "WS"}, headers=headers)
    ws_id = ws_resp.json()["id"]
    
    proj_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Project"},
        headers=headers,
    )
    proj_id = proj_resp.json()["id"]
    return ws_id, proj_id


def test_task_crud_flow(client: TestClient) -> None:
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    ws_id, proj_id = create_workspace_and_project(client, token)
    
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]

    # 1. Create task
    create_resp = client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={
            "title": "First Task",
            "description": "Desc",
            "priority": "HIGH"
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    task = create_resp.json()
    assert task["title"] == "First Task"
    assert task["status"] == "TODO"
    assert task["priority"] == "HIGH"
    assert task["assignee_id"] is None
    task_id = task["id"]

    # 2. Get task
    get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "First Task"

    # 3. Update task
    patch_resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": "IN_PROGRESS",
            "assignee_id": user_id
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "IN_PROGRESS"
    assert updated["assignee_id"] == user_id

    # 4. List tasks with filter
    list_resp = client.get(
        f"/api/v1/projects/{proj_id}/tasks?status=IN_PROGRESS&limit=10",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == task_id
    
    # 5. Delete task
    del_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert del_resp.status_code == 204
    
    # Verify deleted
    assert client.get(f"/api/v1/tasks/{task_id}", headers=headers).status_code == 404


def test_task_authorization(client: TestClient) -> None:
    owner_token = get_token(client, "owner@test.com")
    viewer_token = get_token(client, "viewer@test.com")
    
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    
    ws_id, proj_id = create_workspace_and_project(client, owner_token)
    viewer_id = client.get("/api/v1/users/me", headers=viewer_headers).json()["id"]
    
    # Add viewer to workspace
    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"user_id": viewer_id, "role": "VIEWER"},
        headers=owner_headers,
    )
    
    # Owner creates task
    task_id = client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"title": "Task"},
        headers=owner_headers,
    ).json()["id"]
    
    # Viewer cannot create task
    assert client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"title": "Viewer Task"},
        headers=viewer_headers,
    ).status_code == 403
    
    # Viewer can read task
    assert client.get(f"/api/v1/tasks/{task_id}", headers=viewer_headers).status_code == 200
    
    # Viewer cannot update task
    assert client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "DONE"},
        headers=viewer_headers,
    ).status_code == 403
    
    # Viewer cannot delete task
    assert client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=viewer_headers,
    ).status_code == 403
