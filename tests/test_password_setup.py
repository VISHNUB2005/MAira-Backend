import time

import pytest

from modules.m_auth.m_auth_password_setup import (
    InvalidRegistrationToken,
    PasswordSetupNotAllowed,
    PasswordSetupService,
)
from modules.m_auth.m_auth_pw_security import verify_password


class FakeTokenService:
    def __init__(self, claims=None):
        self.claims = claims if claims is not None else {
            "email": "student@example.com",
            "jti": "test-jti-123",
            "exp": time.time() + 900,
        }
        self.verified_tokens = []

    def verify_registration_token(self, token):
        self.verified_tokens.append(token)
        return self.claims


class FakeUserRepository:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.saved_email = None
        self.saved_hash = None
        self.saved_jti = None
        self.saved_expiry = None

    def complete_password_setup(self, email, password_hash, jti, expires_at):
        self.saved_email = email
        self.saved_hash = password_hash
        self.saved_jti = jti
        self.saved_expiry = expires_at
        return self.allowed


def test_successful_password_setup():
    tokens = FakeTokenService()
    users = FakeUserRepository()
    service = PasswordSetupService(tokens, users)

    result = service.setup_password("valid-token", "StrongPassword@123")

    assert result is None
    assert users.saved_email == "student@example.com"
    assert users.saved_jti == "test-jti-123"
    assert users.saved_expiry == tokens.claims["exp"]
    assert verify_password("StrongPassword@123", users.saved_hash)
    assert users.saved_hash != "StrongPassword@123"


@pytest.mark.parametrize("token", ["expired-token", "replayed-token"])
def test_invalid_or_replayed_token_rejected(token):
    tokens = FakeTokenService(claims={})
    users = FakeUserRepository()
    service = PasswordSetupService(tokens, users)

    with pytest.raises(InvalidRegistrationToken):
        service.setup_password(token, "StrongPassword@123")

    assert users.saved_hash is None


def test_missing_token_rejected():
    service = PasswordSetupService(FakeTokenService(), FakeUserRepository())

    with pytest.raises(InvalidRegistrationToken):
        service.setup_password("", "StrongPassword@123")


def test_ineligible_account_rejected():
    tokens = FakeTokenService()
    users = FakeUserRepository(allowed=False)
    service = PasswordSetupService(tokens, users)

    with pytest.raises(PasswordSetupNotAllowed):
        service.setup_password("valid-token", "StrongPassword@123")


def test_password_hash_is_never_returned():
    service = PasswordSetupService(FakeTokenService(), FakeUserRepository())

    result = service.setup_password("valid-token", "StrongPassword@123")

    assert result is None


def test_invalid_token_does_not_save_password():
    tokens = FakeTokenService(claims={})
    users = FakeUserRepository()
    service = PasswordSetupService(tokens, users)

    with pytest.raises(InvalidRegistrationToken):
        service.setup_password("invalid-token", "StrongPassword@123")

    assert users.saved_hash is None


def test_empty_password_is_rejected():
    tokens = FakeTokenService()
    users = FakeUserRepository()
    service = PasswordSetupService(tokens, users)

    with pytest.raises(ValueError):
        service.setup_password("valid-token", "")

    assert tokens.verified_tokens == []
    assert users.saved_hash is None
