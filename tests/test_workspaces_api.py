"""Integration tests for the Workspace API."""

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


def get_token(client: TestClient, email: str = "owner@test.com") -> str:
    """Helper to register and login a user, returning the access token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": "password123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


def test_workspace_full_flow(api_client: TestClient) -> None:
    # 1. Register and login owner
    owner_token = get_token(api_client, "owner@test.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Create workspace
    resp = api_client.post(
        "/api/v1/workspaces",
        json={"name": "Engineering Team"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    workspace_data = resp.json()
    assert workspace_data["name"] == "Engineering Team"
    workspace_id = workspace_data["id"]

    # 3. GET workspace (Owner)
    resp = api_client.get(f"/api/v1/workspaces/{workspace_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert len(resp.json()["members"]) == 1
    assert resp.json()["members"][0]["role"] == "OWNER"

    # 4. Register and login member
    member_token = get_token(api_client, "member@test.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    member_id = None

    # We need the member's user_id. We can get it from /api/v1/users/me
    resp = api_client.get("/api/v1/users/me", headers=member_headers)
    member_id = resp.json()["id"]

    # 5. Owner invite member EDITOR
    resp = api_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": member_id, "role": "EDITOR"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "EDITOR"

    # 6. Member GET workspace thành công
    resp = api_client.get(f"/api/v1/workspaces/{workspace_id}", headers=member_headers)
    assert resp.status_code == 200
    assert len(resp.json()["members"]) == 2

    # 7. Member không thể invite/remove
    new_member_token = get_token(api_client, "new@test.com")
    resp_me = api_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {new_member_token}"}
    )
    new_member_id = resp_me.json()["id"]

    resp = api_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": new_member_id, "role": "VIEWER"},
        headers=member_headers,
    )
    assert resp.status_code == 403

    resp = api_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_token}",
        headers=member_headers,
    )
    assert resp.status_code == 403

    # 8. Owner remove member
    resp = api_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 204

    # 9. Member GET workspace trả 403
    resp = api_client.get(f"/api/v1/workspaces/{workspace_id}", headers=member_headers)
    assert resp.status_code == 403


def test_workspace_errors_and_edge_cases(api_client: TestClient) -> None:
    owner_token = get_token(api_client, "owner2@test.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Missing bearer
    resp = api_client.post("/api/v1/workspaces", json={"name": "Test"})
    assert resp.status_code == 401

    # Create workspace to test on
    resp = api_client.post("/api/v1/workspaces", json={"name": "Test"}, headers=owner_headers)
    workspace_id = resp.json()["id"]
    owner_id = resp.json()["owner_id"]

    # Workspace UUID invalid
    resp = api_client.get("/api/v1/workspaces/not-a-uuid", headers=owner_headers)
    assert resp.status_code == 422

    # Workspace missing
    import uuid

    missing_id = str(uuid.uuid4())
    resp = api_client.get(f"/api/v1/workspaces/{missing_id}", headers=owner_headers)
    assert resp.status_code == 404

    # Duplicate invite
    member_token = get_token(api_client, "member2@test.com")
    resp_me = api_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {member_token}"}
    )
    member_id = resp_me.json()["id"]

    api_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": member_id, "role": "EDITOR"},
        headers=owner_headers,
    )

    resp = api_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": member_id, "role": "VIEWER"},
        headers=owner_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "workspace_member_already_exists"
    assert "request_id" in resp.json()
    assert "X-Request-ID" in resp.headers

    # Invite OWNER
    new_member_token = get_token(api_client, "new2@test.com")
    resp_me = api_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {new_member_token}"}
    )
    new_member_id = resp_me.json()["id"]
    resp = api_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": new_member_id, "role": "OWNER"},
        headers=owner_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_workspace_role"

    # Remove owner
    resp = api_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "workspace_owner_removal_forbidden"


def test_admin_can_manage_without_membership(api_client: TestClient) -> None:
    # We will test admin behavior in unit tests (test_workspaces_dependencies.py)
    # as the database defaults to MEMBER for new registrations.
    pass


def test_openapi_schema(api_client: TestClient) -> None:
    resp = api_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    paths = schema["paths"]
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/workspaces/{workspace_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/members" in paths
    assert "/api/v1/workspaces/{workspace_id}/members/{user_id}" in paths

    # Check security requirement on workspace routes
    workspace_post = paths["/api/v1/workspaces"]["post"]
    assert "security" in workspace_post
    assert any("HTTPBearer" in sec for sec in workspace_post["security"])


def test_workspace_boundary_access(api_client: TestClient) -> None:
    # Workspace A
    owner_a_token = get_token(api_client, "ownerA@test.com")
    resp_a = api_client.post(
        "/api/v1/workspaces",
        json={"name": "Workspace A"},
        headers={"Authorization": f"Bearer {owner_a_token}"},
    )
    workspace_a_id = resp_a.json()["id"]

    # Workspace B
    owner_b_token = get_token(api_client, "ownerB@test.com")
    resp_b = api_client.post(
        "/api/v1/workspaces",
        json={"name": "Workspace B"},
        headers={"Authorization": f"Bearer {owner_b_token}"},
    )
    workspace_b_id = resp_b.json()["id"]

    # Owner A trying to access Workspace B should fail
    resp = api_client.get(
        f"/api/v1/workspaces/{workspace_b_id}", headers={"Authorization": f"Bearer {owner_a_token}"}
    )
    assert resp.status_code == 403

    # Owner B trying to access Workspace A should fail
    resp = api_client.get(
        f"/api/v1/workspaces/{workspace_a_id}", headers={"Authorization": f"Bearer {owner_b_token}"}
    )
    assert resp.status_code == 403
