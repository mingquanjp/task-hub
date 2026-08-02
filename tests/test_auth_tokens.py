"""Unit tests for JWT issuance and refresh-token hashing."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr

from taskhub.core.config import SecuritySettings
from taskhub.modules.auth.tokens import InvalidTokenErrorDomain, TokenService


def make_token_service() -> TokenService:
    return TokenService(SecuritySettings(jwt_secret_key=SecretStr("test-secret-key-" + "x" * 32)))


def test_token_service_issues_verifiable_access_and_refresh_tokens() -> None:
    service = make_token_service()
    user_id = uuid4()

    pair = service.issue_pair(user_id, now=datetime.now(UTC))
    claims = service.decode_refresh(pair.refresh_token)

    assert claims.user_id == user_id
    assert claims.token_id == pair.refresh_token_id
    assert pair.expires_in == 900
    assert service.hash_refresh_token(pair.refresh_token) != pair.refresh_token


def test_token_service_rejects_access_tokens_as_refresh_tokens() -> None:
    service = make_token_service()
    pair = service.issue_pair(uuid4())

    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_refresh(pair.access_token)


def test_token_service_rejects_expired_refresh_tokens() -> None:
    service = make_token_service()
    pair = service.issue_pair(uuid4(), now=datetime.now(UTC) - timedelta(days=8))

    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_refresh(pair.refresh_token)


def test_token_service_decodes_access_token() -> None:
    service = make_token_service()
    user_id = uuid4()
    pair = service.issue_pair(user_id)

    assert service.decode_access(pair.access_token) == user_id


def test_token_service_rejects_refresh_tokens_as_access_tokens() -> None:
    service = make_token_service()
    pair = service.issue_pair(uuid4())

    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_access(pair.refresh_token)


def test_token_service_rejects_expired_access_tokens() -> None:
    service = make_token_service()
    pair = service.issue_pair(uuid4(), now=datetime.now(UTC) - timedelta(minutes=20))

    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_access(pair.access_token)


def test_token_service_rejects_invalid_signature_and_claims() -> None:
    service = make_token_service()
    pair = service.issue_pair(uuid4())

    # Tamper with the token signature
    tampered_token = pair.access_token[:-5] + "aaaaa"
    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_access(tampered_token)

    # Invalid issuer or audience would also be rejected
    # (tested implicitly by jwt.decode with verify options if we mock a token with wrong claims)
    import jwt

    from taskhub.core.config import SecuritySettings

    settings = SecuritySettings(jwt_secret_key=SecretStr("test-secret-key-" + "x" * 32))

    # Invalid sub (not a UUID)
    bad_sub_token = jwt.encode(
        {"sub": "not-a-uuid", "type": "access", "iss": "taskhub", "aud": "taskhub"},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_access(bad_sub_token)

    # Invalid issuer
    bad_iss_token = jwt.encode(
        {"sub": str(uuid4()), "type": "access", "iss": "wrong-iss", "aud": "taskhub"},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenErrorDomain):
        service.decode_access(bad_iss_token)
