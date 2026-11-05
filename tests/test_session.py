
import jwt

from datetime import datetime, timedelta, timezone

from modules.m_auth.m_auth_sm_session import (
    create_access_token,
    verify_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
    register_refresh_token,
    create_session_tokens,
    refresh_session,
    revoke_refresh_token,
    revoke_session,
    logout,
)

TEST_SECRET = "this-is-a-test-secret-key-at-least-32-bytes-long"


def test_valid_access_token():
    token = create_access_token(
        "user123", "session456", TEST_SECRET,
        "test@example.com", "student"
    )

    payload = verify_access_token(token, TEST_SECRET)

    assert payload["sub"] == "user123"
    assert payload["sid"] == "session456"
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "student"


def test_wrong_secret_rejected():
    token = create_access_token("user123", "session456", TEST_SECRET)

    assert verify_access_token(
        token, "another-test-secret-key-at-least-32-bytes-long"
    ) is None


def test_expired_access_token():
    payload = {
        "sub": "user123",
        "sid": "session456",
        "jti": "test123",
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        "iss": "maira-backend",
        "aud": "maira-api"
    }

    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")

    assert verify_access_token(token, TEST_SECRET) is None


def test_refresh_token_hashing():
    token = create_refresh_token()
    stored_hash = hash_refresh_token(token)

    assert len(stored_hash) == 64
    assert stored_hash != token


def test_refresh_token_verification():
    token = create_refresh_token()
    stored_hash = hash_refresh_token(token)

    assert verify_refresh_token(token, stored_hash)
    assert not verify_refresh_token("wrong-token", stored_hash)


def test_create_session_tokens():
    result = create_session_tokens(
        "user789", "session789", TEST_SECRET,
        "user@example.com", "admin"
    )

    assert result["access_token"]
    assert result["refresh_token"]
    assert result["token_type"] == "bearer"


def test_refresh_session_rotation():
    result = create_session_tokens(
        "user101", "session101", TEST_SECRET
    )

    new_result = refresh_session(
        result["refresh_token"], TEST_SECRET
    )

    assert new_result is not None
    assert new_result["access_token"]
    assert new_result["refresh_token"] != result["refresh_token"]

    # Old refresh token cannot be reused.
    assert refresh_session(
        result["refresh_token"], TEST_SECRET
    ) is None


def test_invalid_refresh_token():
    assert refresh_session("invalid-token", TEST_SECRET) is None


def test_revoke_refresh_token():
    token = create_refresh_token()

    register_refresh_token(
        token, "user202", "session202"
    )

    assert revoke_refresh_token(token) is True
    assert refresh_session(token, TEST_SECRET) is None


def test_logout_revokes_session():
    result = create_session_tokens(
        "user303", "session303", TEST_SECRET
    )

    assert logout("session303") is True

    assert verify_access_token(
        result["access_token"], TEST_SECRET
    ) is None

    assert refresh_session(
        result["refresh_token"], TEST_SECRET
    ) is None


def test_revoke_session():
    token = create_access_token(
        "user404", "session404", TEST_SECRET
    )

    assert revoke_session("session404") is True
    assert verify_access_token(token, TEST_SECRET) is None


