"""Tests for middlewares and error handlers."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from taskhub.api.errors import (
    domain_error_handler,
    internal_error_handler,
)
from taskhub.api.middlewares import RequestContextMiddleware, RequestLoggingMiddleware
from taskhub.core.exceptions import DomainError, InvalidCredentialsError


@pytest.fixture
def app() -> FastAPI:
    fastapi_app = FastAPI()
    fastapi_app.add_middleware(RequestLoggingMiddleware)
    fastapi_app.add_middleware(RequestContextMiddleware)

    fastapi_app.add_exception_handler(DomainError, domain_error_handler)
    fastapi_app.add_exception_handler(Exception, internal_error_handler)

    @fastapi_app.get("/success")
    def success() -> dict[str, str]:
        return {"status": "ok"}

    @fastapi_app.get("/domain-error")
    def domain_error() -> None:
        raise InvalidCredentialsError()

    @fastapi_app.get("/internal-error")
    def internal_error() -> None:
        raise ValueError("Something went wrong")

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_request_id_is_generated_and_returned(client: TestClient) -> None:
    response = client.get("/success")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != "unknown"


def test_request_id_is_preserved_if_provided(client: TestClient) -> None:
    response = client.get("/success", headers={"X-Request-ID": "test-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-123"


def test_domain_error_handler_includes_request_id(client: TestClient) -> None:
    response = client.get("/domain-error", headers={"X-Request-ID": "test-domain"})
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "test-domain"
    data = response.json()
    assert data["code"] == "invalid_credentials"
    assert data["request_id"] == "test-domain"


@pytest.mark.asyncio
async def test_internal_error_route_returns_500_and_hides_details(app: FastAPI) -> None:
    import httpx

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        response = await async_client.get("/internal-error", headers={"X-Request-ID": "test-internal"})

    assert response.status_code == 500
    assert response.headers.get("X-Request-ID") == "test-internal"

    data = response.json()
    assert data["code"] == "internal_error"
    assert data["request_id"] == "test-internal"
    assert "ValueError" not in data["message"]
