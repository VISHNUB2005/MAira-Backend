"""Unit tests for core security, password hashing, and redaction."""

import pytest
from app.core.security import hash_password, verify_password
from app.security.secrets import mask_secret
from app.utils.redaction import mask_email, redact_sensitive_dict


def test_password_hashing_and_verification():
    plain = "InstitutionalPassword123!"
    pw_hash = hash_password(plain)

    assert pw_hash != plain
    assert pw_hash.startswith("$2b$") or pw_hash.startswith("$2a$")
    assert verify_password(plain, pw_hash) is True
    assert verify_password("WrongPassword!", pw_hash) is False


def test_verify_password_with_null_and_empty():
    assert verify_password("", "$2b$12$somehash") is False
    assert verify_password("Password123!", None) is False
    assert verify_password("Password123!", "") is False


def test_hash_password_empty_raises():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")


def test_secret_masking():
    assert mask_secret("") == "<empty>"
    assert mask_secret(None) == "<empty>"
    masked = mask_secret("super_secret_db_password_12345", visible_chars=3)
    assert masked.startswith("sup")
    assert masked.endswith("345")
    assert "*" in masked


def test_email_masking():
    assert mask_email("student@example.com") == "s*****t@example.com"
    assert mask_email("ab@domain.com") == "a*@domain.com"
    assert mask_email("invalid-email") == "invalid-email"


def test_sensitive_dict_redaction():
    payload = {
        "user_id": 1,
        "email": "student@institution.edu",
        "password": "SecretPassword123!",
        "token": "eyJhbGciOi...",
        "nested": {
            "refresh_token": "secret_refresh",
            "safe_field": "visible",
        },
    }
    redacted = redact_sensitive_dict(payload)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["refresh_token"] == "[REDACTED]"
    assert redacted["nested"]["safe_field"] == "visible"
    assert redacted["email"] == "student@institution.edu"
