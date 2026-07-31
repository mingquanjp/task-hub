"""JWT access/refresh token issuance and verification."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from taskhub.core.config import SecuritySettings


class InvalidTokenErrorDomain(Exception):
    """Raised when a JWT cannot be trusted or has the wrong token type."""


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Credentials and access-token lifetime returned by the token service."""

    access_token: str
    refresh_token: str
    expires_in: int
    refresh_token_id: UUID
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshClaims:
    """Validated identity claims extracted from a refresh JWT."""

    user_id: UUID
    token_id: UUID


class TokenService:
    """Issue and verify signed JWTs without knowing HTTP or persistence."""

    def __init__(self, settings: SecuritySettings) -> None:
        self._settings = settings

    def issue_pair(self, user_id: UUID, *, now: datetime | None = None) -> TokenPair:
        current = now or datetime.now(UTC)
        refresh_token_id = uuid4()
        access_expires_at = current + timedelta(
            minutes=self._settings.jwt_access_token_expire_minutes
        )
        refresh_expires_at = current + timedelta(days=self._settings.jwt_refresh_token_expire_days)
        access_token = self._encode(
            {"sub": str(user_id), "type": "access"},
            issued_at=current,
            expires_at=access_expires_at,
        )
        refresh_token = self._encode(
            {"sub": str(user_id), "jti": str(refresh_token_id), "type": "refresh"},
            issued_at=current,
            expires_at=refresh_expires_at,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.jwt_access_token_expire_minutes * 60,
            refresh_token_id=refresh_token_id,
            refresh_expires_at=refresh_expires_at,
        )

    def decode_refresh(self, token: str) -> RefreshClaims:
        """Verify issuer, audience, signature, expiry and refresh-token type."""
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
            )
            if payload.get("type") != "refresh":
                raise InvalidTokenErrorDomain
            user_id = UUID(str(payload["sub"]))
            token_id = UUID(str(payload["jti"]))
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenErrorDomain from exc
        return RefreshClaims(user_id=user_id, token_id=token_id)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Return the deterministic DB lookup hash for a raw refresh token."""
        return sha256(token.encode("utf-8"), usedforsecurity=True).hexdigest()

    def _encode(
        self,
        claims: dict[str, str],
        *,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
        payload = {
            **claims,
            "iat": issued_at,
            "exp": expires_at,
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
        )
