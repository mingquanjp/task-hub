"""Tests for FastAPI wiring of label dependencies and transactions."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.application import create_app
from taskhub.core.config import SecuritySettings
from taskhub.modules.labels.dependencies import (
    LabelServiceDep,
    get_db_session,
    get_label_repository,
    get_label_service,
)
from taskhub.modules.labels.sqlalchemy_repository import SQLAlchemyLabelRepository


class SessionFactory:
    """Small async context-manager factory for transaction dependency tests."""

    def __init__(self, session: MagicMock) -> None:
        self._session = session

    def __call__(self) -> "SessionFactory":
        return self

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def make_request(session: MagicMock) -> Request:
    """Create a request carrying an AsyncSession-shaped factory."""
    app = create_app()
    app.state.session_factory = SessionFactory(session)
    return Request({"type": "http", "app": app})


def test_dependencies_build_a_sqlalchemy_repository_from_a_request_session() -> None:
    session = MagicMock(spec=AsyncSession)

    repository = get_label_repository(session)
    service = get_label_service(repository)

    assert isinstance(repository, SQLAlchemyLabelRepository)
    assert repository._session is session
    assert service._repository is repository


def test_each_application_builds_its_own_database_resources(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    first_app = create_app(database_url=database_url, security_settings=security_settings)
    second_app = create_app(database_url=database_url, security_settings=security_settings)

    with TestClient(first_app), TestClient(second_app):
        assert first_app.state.engine is not second_app.state.engine
        assert first_app.state.session_factory is not second_app.state.session_factory


def test_fastapi_resolves_the_label_service_dependency(
    database_url: str,
    security_settings: SecuritySettings,
) -> None:
    app = create_app(database_url=database_url, security_settings=security_settings)
    session = MagicMock(spec=AsyncSession)

    async def override_db_session() -> object:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session

    @app.get("/_test/label-service")
    def read_service(service: LabelServiceDep) -> dict[str, bool]:
        has_sqlalchemy_repository = isinstance(service._repository, SQLAlchemyLabelRepository)
        return {"has_sqlalchemy_repository": has_sqlalchemy_repository}

    with TestClient(app) as client:
        response = client.get("/_test/label-service")

    assert response.status_code == 200
    assert response.json() == {"has_sqlalchemy_repository": True}


@pytest.mark.asyncio
async def test_db_session_commits_after_a_successful_request() -> None:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    sessions = get_db_session(make_request(session))

    assert await anext(sessions) is session
    with pytest.raises(StopAsyncIteration):
        await anext(sessions)

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_db_session_rolls_back_when_commit_fails() -> None:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    session.rollback = AsyncMock()
    sessions = get_db_session(make_request(session))

    assert await anext(sessions) is session
    with pytest.raises(RuntimeError, match="commit failed"):
        await anext(sessions)

    session.rollback.assert_awaited_once()
