"""Password hashing boundary for authentication use cases."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


class PasswordHasher:
    """Hash and verify passwords with the recommended Argon2 configuration."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        """Return a one-way Argon2 password hash."""
        return self._password_hash.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        """Check a plaintext password against a stored hash."""
        try:
            return self._password_hash.verify(password, hashed_password)
        except UnknownHashError:
            return False
