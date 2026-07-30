"""Integration tests for label HTTP endpoints."""

import asyncio
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.modules.labels.dependencies import get_label_repository
from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.repository import InMemoryLabelRepository


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create an isolated application client with its lifespan active."""
    with TestClient(create_app()) as test_client:
        yield test_client


def test_label_crud_happy_path(client: TestClient) -> None:
    project_id = uuid4()
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
    response = client.post(path, json=payload)

    assert response.status_code == 422


def test_label_endpoints_handle_empty_patch_not_found_and_wrong_project(client: TestClient) -> None:
    project_id = uuid4()
    other_project_id = uuid4()
    base_path = f"/api/v1/projects/{project_id}/labels"
    created = client.post(base_path, json={"name": "Backend", "color": "#1A73E8"}).json()
    label_path = f"{base_path}/{created['id']}"

    assert client.patch(label_path, json={}).status_code == 422
    assert client.get(f"{base_path}/not-a-uuid").status_code == 422
    assert client.get(f"{base_path}/{uuid4()}").status_code == 404
    assert (
        client.get(f"/api/v1/projects/{other_project_id}/labels/{created['id']}").status_code == 404
    )


def test_application_instances_isolate_label_data() -> None:
    first_app = create_app()
    second_app = create_app()
    project_id = uuid4()
    path = f"/api/v1/projects/{project_id}/labels"

    with TestClient(first_app) as first_client, TestClient(second_app) as second_client:
        assert (
            first_client.post(path, json={"name": "Backend", "color": "#1A73E8"}).status_code == 201
        )
        assert len(first_client.get(path).json()) == 1
        assert second_client.get(path).json() == []


def test_dependency_override_replaces_the_label_repository() -> None:
    app = create_app()
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
