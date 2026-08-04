"""Unit tests for the Task Labels API."""

from collections.abc import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings
from taskhub.core.passwords import PasswordHasher
from taskhub.infrastructure.database.models.label import LabelModel
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
        json={"email": "user_labels@example.com", "password": "Password123!"},
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
async def setup_label_data(database_url: str, api_client: TestClient) -> dict[str, str]:
    """Set up data for task label tests."""
    database = Database(database_url)
    user_id = uuid4()
    viewer_id = uuid4()
    non_member_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    other_project_id = uuid4()
    task_id = uuid4()
    label_id = uuid4()
    other_label_id = uuid4()

    async with database.session_factory() as session:
        hashed_pw = PasswordHasher().hash("Password123!")
        session.add(
            UserModel(
                id=user_id,
                email="user_labels@example.com",
                hashed_password=hashed_pw,
                full_name="User L",
            )
        )
        session.add(
            UserModel(
                id=viewer_id,
                email="viewer_labels@example.com",
                hashed_password=hashed_pw,
                full_name="Viewer",
            )
        )
        session.add(
            UserModel(
                id=non_member_id,
                email="non_member_labels@example.com",
                hashed_password=hashed_pw,
                full_name="Non Member",
            )
        )
        session.add(WorkspaceModel(id=workspace_id, name="Workspace L", owner_id=user_id))
        session.add(WorkspaceMemberModel(workspace_id=workspace_id, user_id=user_id, role="OWNER"))
        session.add(
            WorkspaceMemberModel(workspace_id=workspace_id, user_id=viewer_id, role="VIEWER")
        )
        session.add(
            ProjectModel(
                id=project_id, workspace_id=workspace_id, name="Project L", status="ACTIVE"
            )
        )
        session.add(
            ProjectModel(
                id=other_project_id,
                workspace_id=workspace_id,
                name="Other Project",
                status="ACTIVE",
            )
        )

        session.add(
            TaskModel(
                id=task_id,
                project_id=project_id,
                title="Task L",
                status="TODO",
                priority="MEDIUM",
                created_by=user_id,
            )
        )
        session.add(
            LabelModel(
                id=label_id,
                project_id=project_id,
                name="Bug",
                color="#FF0000",
            )
        )
        session.add(
            LabelModel(
                id=other_label_id,
                project_id=other_project_id,
                name="Enhancement",
                color="#00FF00",
            )
        )
        await session.commit()

    return {
        "task_id": str(task_id),
        "label_id": str(label_id),
        "other_label_id": str(other_label_id),
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
async def test_attach_and_detach_label(
    api_client: TestClient, setup_label_data: dict[str, str]
) -> None:
    task_id = setup_label_data["task_id"]
    label_id = setup_label_data["label_id"]
    token = get_token(api_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Attach label
    resp = api_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers)
    assert resp.status_code == 201

    # Attach again should conflict
    resp = api_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers)
    assert resp.status_code == 409

    # Detach label
    resp = api_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers)
    assert resp.status_code == 204

    # Detach again should be idempotent 204 or just return 204
    resp = api_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_task_label_authorization(
    api_client: TestClient, setup_label_data: dict[str, str]
) -> None:
    task_id = setup_label_data["task_id"]
    label_id = setup_label_data["label_id"]
    other_label_id = setup_label_data["other_label_id"]

    # VIEWER tries to attach label -> 403
    token_viewer = get_token_for(api_client, "viewer_labels@example.com")
    headers_viewer = {"Authorization": f"Bearer {token_viewer}"}
    resp = api_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers_viewer)
    assert resp.status_code == 403

    # Non-member tries to attach label -> 403
    token_non_member = get_token_for(api_client, "non_member_labels@example.com")
    headers_non_member = {"Authorization": f"Bearer {token_non_member}"}
    resp = api_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers_non_member)
    assert resp.status_code == 403

    # OWNER tries to attach a label from another project -> 409
    token_owner = get_token_for(api_client, "user_labels@example.com")
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    resp = api_client.post(
        f"/api/v1/tasks/{task_id}/labels/{other_label_id}", headers=headers_owner
    )
    assert resp.status_code == 409

    # OWNER attaches valid label -> 201
    resp = api_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers_owner)
    assert resp.status_code == 201

    # VIEWER tries to detach label -> 403
    resp = api_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers_viewer)
    assert resp.status_code == 403

    # OWNER detaches valid label -> 204
    resp = api_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=headers_owner)
    assert resp.status_code == 204
