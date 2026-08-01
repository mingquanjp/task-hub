"""Users application use cases independent from FastAPI and SQLAlchemy."""

import dataclasses
from datetime import UTC, datetime
from uuid import UUID

from anyio import to_thread

from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.entities import User
from taskhub.modules.auth.repository import (
    DuplicateEmailPersistenceError,
    RefreshTokenRepository,
    UserRepository,
)


class EmailAlreadyInUseError(Exception):
    """Raised when an update attempts to use an email already claimed by another user."""


class IncorrectCurrentPasswordError(Exception):
    """Raised when attempting to change a password with an incorrect current password."""


class UserNotFoundError(Exception):
    """Raised when updating a user that no longer exists."""


class UserService:
    """Coordinate user profile and credential updates."""

    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._password_hasher = password_hasher

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None = None,
        email: str | None = None,
    ) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        if email is not None:
            email = self._normalize_email(email)

        if email is not None or full_name is not None:
            user = dataclasses.replace(
                user,
                email=email if email is not None else user.email,
                full_name=full_name if full_name is not None else user.full_name,
            )

        try:
            return await self._users.update(user)
        except DuplicateEmailPersistenceError as exc:
            raise EmailAlreadyInUseError from exc

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        if not await to_thread.run_sync(
            self._password_hasher.verify,
            current_password,
            user.hashed_password,
        ):
            raise IncorrectCurrentPasswordError

        new_hashed_password = await to_thread.run_sync(self._password_hasher.hash, new_password)
        user = dataclasses.replace(user, hashed_password=new_hashed_password)
        await self._users.update(user)
        await self._refresh_tokens.revoke_all_for_user(user.id, datetime.now(UTC))

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
