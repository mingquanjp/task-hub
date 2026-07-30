"""Tests for FastAPI wiring of label dependencies."""

from fastapi import Request
from fastapi.testclient import TestClient

from taskhub.application import create_app
from taskhub.modules.labels.dependencies import (
    LabelServiceDep,
    get_label_repository,
    get_label_service,
)
from taskhub.modules.labels.repository import InMemoryLabelRepository


def test_dependencies_use_the_application_scoped_repository() -> None:
    app = create_app()
    request = Request({"type": "http", "app": app})

    repository = get_label_repository(request)
    service = get_label_service(repository)

    assert repository is app.state.label_repository
    assert isinstance(repository, InMemoryLabelRepository)
    assert service._repository is repository


def test_each_application_has_its_own_repository() -> None:
    first_app = create_app()
    second_app = create_app()

    assert first_app.state.label_repository is not second_app.state.label_repository


def test_fastapi_resolves_the_label_service_dependency() -> None:
    app = create_app()

    @app.get("/_test/label-service")
    def read_service(service: LabelServiceDep) -> dict[str, bool]:
        has_in_memory_repository = isinstance(service._repository, InMemoryLabelRepository)
        return {"has_in_memory_repository": has_in_memory_repository}

    with TestClient(app) as client:
        response = client.get("/_test/label-service")

    assert response.status_code == 200
    assert response.json() == {"has_in_memory_repository": True}
