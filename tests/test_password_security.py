import pytest

from modules.m_auth.m_auth_pw_security import (
    hash_password,
    verify_password,
)


def test_password_is_hashed():
    password = "TestPassword@123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_correct_password_verifies():
    password = "TestPassword@123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_incorrect_password_fails():
    hashed = hash_password("TestPassword@123")

    assert verify_password("WrongPassword@123", hashed) is False


def test_each_hash_uses_a_different_salt():
    password = "TestPassword@123"

    assert hash_password(password) != hash_password(password)


def test_empty_password_is_rejected():
    with pytest.raises(ValueError):
        hash_password("")


def test_invalid_hash_returns_false():
    assert verify_password("SomePassword123", "not-a-valid-hash") is False
