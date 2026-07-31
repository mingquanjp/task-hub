"""Unit tests for password hashing behavior."""

from taskhub.core.passwords import PasswordHasher


def test_password_hasher_uses_one_way_argon2_hashes() -> None:
    hasher = PasswordHasher()
    password = "correct horse battery staple"

    hashed_password = hasher.hash(password)

    assert hashed_password != password
    assert hashed_password.startswith("$argon2id$")
    assert hasher.verify(password, hashed_password) is True
    assert hasher.verify("wrong password", hashed_password) is False


def test_password_hashing_uses_a_new_salt_each_time() -> None:
    hasher = PasswordHasher()
    password = "correct horse battery staple"

    assert hasher.hash(password) != hasher.hash(password)


def test_password_hasher_rejects_a_malformed_stored_hash() -> None:
    assert PasswordHasher().verify("any password", "not-a-valid-hash") is False
