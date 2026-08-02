"""Authentication application use cases independent from FastAPI and SQLAlchemy."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from anyio import to_thread

from taskhub.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.entities import RefreshToken, User, UserRole
from taskhub.modules.auth.repository import (
    DuplicateEmailPersistenceError,
    RefreshTokenRepository,
    UserRepository,
)
from taskhub.modules.auth.tokens import InvalidTokenErrorDomain, TokenService


@dataclass(frozen=True, slots=True)
class AuthResult:
    """New credentials and their public user representation."""

    user: User
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    """Coordinate registration, login, refresh rotation and logout."""

    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def register(self, email: str, full_name: str, password: str) -> User:
        normalized_email = self._normalize_email(email)
        if await self._users.get_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError
        now = datetime.now(UTC)
        user = User(
            id=uuid4(),
            email=normalized_email,
            full_name=full_name,
            hashed_password=await to_thread.run_sync(self._password_hasher.hash, password),
            role=UserRole.MEMBER,
            is_active=True,
            created_at=now,
        )
        try:
            return await self._users.create(user)
        except DuplicateEmailPersistenceError as exc:
            raise UserAlreadyExistsError from exc

    async def login(self, email: str, password: str) -> AuthResult:
        user = await self._users.get_by_email(self._normalize_email(email))
        if user is None:
            raise InvalidCredentialsError
        if not await to_thread.run_sync(
            self._password_hasher.verify,
            password,
            user.hashed_password,
        ):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return await self._issue_credentials(user)

    async def refresh(self, raw_refresh_token: str) -> AuthResult:
        try:
            claims = self._token_service.decode_refresh(raw_refresh_token)
            stored = await self._refresh_tokens.get_by_hash(
                self._token_service.hash_refresh_token(raw_refresh_token)
            )
        except InvalidTokenErrorDomain as exc:
            raise InvalidTokenError from exc
        now = datetime.now(UTC)
        if stored is None or stored.id != claims.token_id or stored.user_id != claims.user_id:
            raise InvalidTokenError
        if stored.revoked_at is not None:
            raise TokenRevokedError
        if self._as_utc(stored.expires_at) <= now:
            raise InvalidTokenError
        user = await self._users.get_by_id(claims.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError
        if not await self._refresh_tokens.revoke(stored.id, now):
            raise InvalidTokenError
        return await self._issue_credentials(user)

    async def logout(self, raw_refresh_token: str) -> None:
        try:
            claims = self._token_service.decode_refresh(raw_refresh_token)
        except InvalidTokenErrorDomain as exc:
            raise InvalidTokenError from exc
        stored = await self._refresh_tokens.get_by_hash(
            self._token_service.hash_refresh_token(raw_refresh_token)
        )
        if stored is None or stored.id != claims.token_id or stored.user_id != claims.user_id:
            raise InvalidTokenError
        await self._refresh_tokens.revoke(stored.id, datetime.now(UTC))

    async def _issue_credentials(self, user: User) -> AuthResult:
        pair = self._token_service.issue_pair(user.id)
        await self._refresh_tokens.create(
            RefreshToken(
                id=pair.refresh_token_id,
                user_id=user.id,
                token_hash=self._token_service.hash_refresh_token(pair.refresh_token),
                expires_at=pair.refresh_expires_at,
                revoked_at=None,
                created_at=datetime.now(UTC),
            )
        )
        return AuthResult(
            user=user,
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=pair.expires_in,
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """Normalize database timestamps from drivers that drop timezone metadata."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
