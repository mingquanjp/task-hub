"""Tests for security logging and preventing sensitive data leakage."""

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


def test_authorization_header_and_tokens_are_not_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    # Hit any endpoint with a fake Authorization header
    # and ensure it doesn't log the header.
    sensitive_token = "eyJhbGciOiJIUzI1NiIsInR5cCI.sensitivetoken.signature"

    # We expect this to fail with 401 or similar, but the point is to check logs
    client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {sensitive_token}"})

    # Let's also check login payload
    password = "SuperSecretPassword123"
    client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": password})

    log_output = caplog.text

    assert sensitive_token not in log_output, "Access token leaked into logs!"
    assert password not in log_output, "Password leaked into logs!"
    assert "Authorization" not in log_output, "Authorization header leaked into logs!"
