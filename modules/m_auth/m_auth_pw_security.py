"""Password hashing and verification utilities for MAira."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a secure Argon2id hash for a password."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string.")
    if not password:
        raise ValueError("Password cannot be empty.")

    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not plain_password or not hashed_password:
        return False

    try:
        return _password_hasher.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False
