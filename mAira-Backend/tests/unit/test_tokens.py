"""Unit tests for JWT access tokens, refresh tokens, and MFA tokens."""

from datetime import datetime, timezone
import pytest
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    create_registration_ticket,
    decode_access_token,
    decode_mfa_challenge_token,
    decode_registration_ticket,
    hash_refresh_token,
    verify_refresh_token,
)

settings = get_settings()


def test_create_and_decode_valid_access_token():
    token = create_access_token(
        user_id=42,
        session_id="97732a39-2a94-4c4f-9e32-23c348f98c8e",
        email="student@example.com",
        role="STUDENT",
        account_type="USER",
        expires_minutes=15,
    )
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["sid"] == "97732a39-2a94-4c4f-9e32-23c348f98c8e"
    assert payload["email"] == "student@example.com"
    assert payload["role"] == "STUDENT"
    assert payload["type"] == "access"
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert "jti" in payload


def test_expired_access_token_rejected():
    token = create_access_token(
        user_id=42,
        session_id="session-123",
        email="user@test.com",
        expires_minutes=-5,
    )
    payload = decode_access_token(token)
    assert payload is None


def test_tampered_access_token_rejected():
    token = create_access_token(
        user_id=42,
        session_id="session-123",
        email="user@test.com",
    )
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None


def test_refresh_token_lifecycle():
    raw_token = create_refresh_token()
    assert isinstance(raw_token, str)
    assert len(raw_token) >= 64

    token_hash = hash_refresh_token(raw_token)
    assert len(token_hash) == 64  # SHA-256 hex string

    # Verification
    assert verify_refresh_token(raw_token, token_hash) is True
    assert verify_refresh_token("invalid_token", token_hash) is False
    assert verify_refresh_token("", token_hash) is False
    assert verify_refresh_token(raw_token, "") is False


def test_registration_ticket_lifecycle():
    otp_id = "11111111-1111-1111-1111-111111111111"
    ticket = create_registration_ticket("newstudent@example.com", user_id=99, otp_id=otp_id)
    assert isinstance(ticket, str)

    payload = decode_registration_ticket(ticket)
    assert payload is not None
    assert payload["sub"] == "99"
    assert payload["email"] == "newstudent@example.com"
    assert payload["otp_id"] == otp_id
    assert payload["type"] == "registration_verified"


def test_mfa_challenge_token_lifecycle():
    otp_id = "22222222-2222-2222-2222-222222222222"
    token = create_mfa_challenge_token(
        account_id=50,
        email="mfauser@example.com",
        role="STUDENT",
        account_type="USER",
        otp_id=otp_id,
        expires_minutes=5,
    )
    assert isinstance(token, str)

    payload = decode_mfa_challenge_token(token)
    assert payload is not None
    assert payload["sub"] == "50"
    assert payload["email"] == "mfauser@example.com"
    assert payload["role"] == "STUDENT"
    assert payload["account_type"] == "USER"
    assert payload["otp_id"] == otp_id
    assert payload["type"] == "mfa_pending"
