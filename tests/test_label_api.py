"""Database-backed integration tests for label HTTP endpoints."""

import asyncio
from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings
from taskhub.infrastructure.database.models import ProjectModel
from taskhub.infrastructure.database.session import Database
from taskhub.modules.labels.dependencies import get_label_repository
from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.repository import InMemoryLabelRepository


async def seed_project(database_url: str, project_id: UUID) -> None:
    """Insert a minimal parent directly because the Project API is not built yet."""
    database = Database(database_url)
    try:
        async with database.session_factory() as session:
            session.add(ProjectModel(id=project_id))
            await session.commit()
    finally:
        await database.dispose()


@pytest.fixture
def client(
    database_url: str,
    security_settings: SecuritySettings,
) -> Generator[TestClient, None, None]:
    """Run one application instance against a migrated temporary database."""
    project_id = uuid4()
    asyncio.run(seed_project(database_url, project_id))
    app = create_app(database_url=database_url, security_settings=security_settings)
    app.state.test_project_id = project_id
    with TestClient(app) as test_client:
        yield test_client


def test_label_crud_happy_path(client: TestClient) -> None:
    project_id = client.app.state.test_project_id
    base_path = f"/api/v1/projects/{project_id}/labels"

    created_response = client.post(base_path, json={"name": "Backend", "color": "#1a73e8"})

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["project_id"] == str(project_id)
    assert created["name"] == "Backend"
    assert created["color"] == "#1A73E8"

    listed_response = client.get(base_path)
    assert listed_response.status_code == 200
    assert listed_response.json() == [created]

    label_path = f"{base_path}/{created['id']}"
    get_response = client.get(label_path)
    assert get_response.status_code == 200
    assert get_response.json() == created

    updated_response = client.patch(label_path, json={"name": "Platform"})
    assert updated_response.status_code == 200
    assert updated_response.json() == {**created, "name": "Platform"}

    deleted_response = client.delete(label_path)
    assert deleted_response.status_code == 204
    assert deleted_response.content == b""
    assert client.get(label_path).status_code == 404


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/projects/not-a-uuid/labels", {"name": "Backend", "color": "#1A73E8"}),
        (
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/labels",
            {"name": "", "color": "#1A73E8"},
        ),
        (
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/labels",
            {"name": "Backend", "color": "blue"},
        ),
    ],
)
def test_create_label_rejects_invalid_path_and_body(
    client: TestClient,
    path: str,
    payload: dict[str, str],
) -> None:
    assert client.post(path, json=payload).status_code == 422


def test_label_endpoints_handle_empty_patch_not_found_and_wrong_project(client: TestClient) -> None:
    project_id = client.app.state.test_project_id
    other_project_id = uuid4()
    base_path = f"/api/v1/projects/{project_id}/labels"
    created = client.post(base_path, json={"name": "Backend", "color": "#1A73E8"}).json()
    label_path = f"{base_path}/{created['id']}"

    assert client.patch(label_path, json={}).status_code == 422
    assert client.get(f"{base_path}/not-a-uuid").status_code == 422
    assert client.get(f"{base_path}/{uuid4()}").status_code == 404
    other_project_label_path = f"/api/v1/projects/{other_project_id}/labels/{created['id']}"
    assert client.get(other_project_label_path).status_code == 404


def test_create_label_returns_404_when_project_is_missing(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{uuid4()}/labels",
        json={"name": "Backend", "color": "#1A73E8"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "resource_not_found"
    assert client.get(f"/api/v1/projects/{uuid4()}/labels").json() == []


def test_label_data_persists_after_application_restart(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    project_id = uuid4()
    asyncio.run(seed_project(database_url, project_id))
    path = f"/api/v1/projects/{project_id}/labels"

    with TestClient(
        create_app(database_url=database_url, security_settings=security_settings)
    ) as first_client:
        response = first_client.post(path, json={"name": "Backend", "color": "#1A73E8"})
        assert response.status_code == 201

    with TestClient(
        create_app(database_url=database_url, security_settings=security_settings)
    ) as second_client:
        assert len(second_client.get(path).json()) == 1


def test_dependency_override_replaces_the_label_repository(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    app = create_app(database_url=database_url, security_settings=security_settings)
    override_repository = InMemoryLabelRepository()
    project_id = uuid4()
    path = f"/api/v1/projects/{project_id}/labels"
    seeded_label = Label(uuid4(), project_id, "Seeded", "#1A73E8")
    asyncio.run(override_repository.create(seeded_label))
    app.dependency_overrides[get_label_repository] = lambda: override_repository

    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(seeded_label.id),
            "project_id": str(project_id),
            "name": "Seeded",
            "color": "#1A73E8",
        }
    ]
