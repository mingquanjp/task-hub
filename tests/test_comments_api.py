"""Unit tests for the Comments API."""

from collections.abc import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings
from taskhub.core.passwords import PasswordHasher
from taskhub.infrastructure.database.models.project import ProjectModel
from taskhub.infrastructure.database.models.task import TaskModel
from taskhub.infrastructure.database.models.user import UserModel
from taskhub.infrastructure.database.models.workspace import WorkspaceModel
from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel
from taskhub.infrastructure.database.session import Database


def get_token(api_client: TestClient) -> str:
    """Helper to get a token."""
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "Password123!"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.text}")
    return str(response.json()["access_token"])


@pytest.fixture
def api_client(
    database_url: str,
    security_settings: SecuritySettings,
) -> Generator[TestClient, None, None]:
    app = create_app(database_url=database_url, security_settings=security_settings)
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def setup_comment_data(database_url: str, api_client: TestClient) -> dict[str, str]:
    """Set up data for comment tests."""
    database = Database(database_url)
    user1_id = uuid4()
    user2_id = uuid4()
    user3_id = uuid4()
    user4_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    task_id = uuid4()

    async with database.session_factory() as session:
        # Create users
        hashed_pw = PasswordHasher().hash("Password123!")
        session.add(
            UserModel(
                id=user1_id,
                email="user1@example.com",
                hashed_password=hashed_pw,
                full_name="User 1",
            )
        )
        session.add(
            UserModel(
                id=user2_id,
                email="user2@example.com",
                hashed_password=hashed_pw,
                full_name="User 2",
            )
        )
        session.add(
            UserModel(
                id=user3_id,
                email="user3@example.com",
                hashed_password=hashed_pw,
                full_name="User 3",
            )
        )
        session.add(
            UserModel(
                id=user4_id,
                email="user4@example.com",
                hashed_password=hashed_pw,
                full_name="User 4",
            )
        )

        # Create workspace and project
        session.add(WorkspaceModel(id=workspace_id, name="Workspace", owner_id=user1_id))
        session.add(WorkspaceMemberModel(workspace_id=workspace_id, user_id=user1_id, role="OWNER"))
        session.add(
            WorkspaceMemberModel(workspace_id=workspace_id, user_id=user2_id, role="EDITOR")
        )
        session.add(
            WorkspaceMemberModel(workspace_id=workspace_id, user_id=user3_id, role="VIEWER")
        )
        session.add(
            ProjectModel(id=project_id, workspace_id=workspace_id, name="Project", status="ACTIVE")
        )

        # Create task
        session.add(
            TaskModel(
                id=task_id,
                project_id=project_id,
                title="Task",
                status="TODO",
                priority="MEDIUM",
                created_by=user1_id,
            )
        )
        await session.commit()

    return {
        "task_id": str(task_id),
        "workspace_id": str(workspace_id),
        "project_id": str(project_id),
    }


def get_token_for(api_client: TestClient, email: str) -> str:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.text}")
    return str(response.json()["access_token"])


@pytest.mark.asyncio
async def test_create_and_list_comments(
    api_client: TestClient, setup_comment_data: dict[str, str]
) -> None:
    task_id = setup_comment_data["task_id"]
    token = get_token(api_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create comment
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "This is a comment"},
        headers=headers,
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    # List comments
    resp = api_client.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == comment_id


@pytest.mark.asyncio
async def test_update_comment(api_client: TestClient, setup_comment_data: dict[str, str]) -> None:
    task_id = setup_comment_data["task_id"]
    token = get_token(api_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create comment
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "Original"}, headers=headers
    )
    comment_id = resp.json()["id"]

    # Update comment
    resp = api_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Updated"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated"


@pytest.mark.asyncio
async def test_delete_comment(api_client: TestClient, setup_comment_data: dict[str, str]) -> None:
    task_id = setup_comment_data["task_id"]
    token = get_token(api_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create comment
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "To be deleted"}, headers=headers
    )
    comment_id = resp.json()["id"]

    # Delete comment
    resp = api_client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        headers=headers,
    )
    assert resp.status_code == 204

    # Verify deletion
    resp = api_client.get(f"/api/v1/tasks/{task_id}/comments", headers=headers)
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_update_comment_authorization(
    api_client: TestClient, setup_comment_data: dict[str, str]
) -> None:
    task_id = setup_comment_data["task_id"]

    # Create comment by User 2 (EDITOR)
    token_user2 = get_token_for(api_client, "user2@example.com")
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "By User 2"}, headers=headers_user2
    )
    comment_id = resp.json()["id"]

    # User 3 (VIEWER) tries to update -> 403
    token_user3 = get_token_for(api_client, "user3@example.com")
    headers_user3 = {"Authorization": f"Bearer {token_user3}"}
    resp = api_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Ha"},
        headers=headers_user3,
    )
    assert resp.status_code == 403

    # User 1 (OWNER) tries to update -> 403 (owners cannot update other's comments)
    token_user1 = get_token_for(api_client, "user1@example.com")
    headers_user1 = {"Authorization": f"Bearer {token_user1}"}
    resp = api_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Ha"},
        headers=headers_user1,
    )
    assert resp.status_code == 403

    # Non-member User 4 tries to update -> 403 (via project member check)
    token_user4 = get_token_for(api_client, "user4@example.com")
    headers_user4 = {"Authorization": f"Bearer {token_user4}"}
    resp = api_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Ha"},
        headers=headers_user4,
    )
    assert resp.status_code == 403

    # User 2 updates their own comment -> 200
    resp = api_client.patch(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}",
        json={"content": "Updated"},
        headers=headers_user2,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_comment_authorization(
    api_client: TestClient, setup_comment_data: dict[str, str]
) -> None:
    task_id = setup_comment_data["task_id"]

    # Create comment by User 3 (VIEWER)
    token_user3 = get_token_for(api_client, "user3@example.com")
    headers_user3 = {"Authorization": f"Bearer {token_user3}"}
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"content": "By User 3"}, headers=headers_user3
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    # User 2 (EDITOR) tries to delete -> 403
    token_user2 = get_token_for(api_client, "user2@example.com")
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}
    resp = api_client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=headers_user2
    )
    assert resp.status_code == 403

    # Non-member User 4 tries to delete -> 403
    token_user4 = get_token_for(api_client, "user4@example.com")
    headers_user4 = {"Authorization": f"Bearer {token_user4}"}
    resp = api_client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=headers_user4
    )
    assert resp.status_code == 403

    # User 1 (OWNER) tries to delete -> 204 (owners can delete any comment)
    token_user1 = get_token_for(api_client, "user1@example.com")
    headers_user1 = {"Authorization": f"Bearer {token_user1}"}
    resp = api_client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=headers_user1
    )
    assert resp.status_code == 204
