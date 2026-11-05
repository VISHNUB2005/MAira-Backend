
from datetime import datetime, timedelta, timezone

import jwt

from modules.m_auth.m_auth_sm_session import (
    create_access_token,
    create_refresh_token,
    create_session_tokens,
    hash_refresh_token,
    logout,
    refresh_session,
    register_refresh_token,
    revoke_refresh_token,
    revoke_session,
    verify_access_token,
    verify_refresh_token,
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




def test_tampered_access_token_rejected():
    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token(
        user_id="user-123",
        session_id="session-123",
        secret_key=secret,
    )

    parts = token.split(".")
    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered_token = ".".join(parts)

    assert verify_access_token(tampered_token, secret) is None



def test_wrong_issuer_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-123", "session-123", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload["iss"] = "wrong-issuer"
    wrong_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(wrong_token, secret) is None


def test_wrong_audience_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-123", "session-123", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload["aud"] = "wrong-audience"
    wrong_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(wrong_token, secret) is None


def test_missing_jwt_secret_rejected(monkeypatch):
    import pytest

    import modules.m_auth.m_auth_sm_session as session

    monkeypatch.setattr(session, "JWT_SECRET_KEY", "")
    with pytest.raises(RuntimeError):
        session.get_jwt_secret_key()


def test_weak_jwt_secret_rejected(monkeypatch):
    import pytest

    import modules.m_auth.m_auth_sm_session as session

    monkeypatch.setattr(session, "JWT_SECRET_KEY", "short-secret")
    with pytest.raises(RuntimeError):
        session.get_jwt_secret_key()


def test_strong_jwt_secret_accepted(monkeypatch):
    import modules.m_auth.m_auth_sm_session as session

    secret = "this-is-a-strong-test-secret-at-least-32"
    monkeypatch.setattr(session, "JWT_SECRET_KEY", secret)
    assert session.get_jwt_secret_key() == secret


def test_malformed_access_token_rejected():
    from modules.m_auth.m_auth_sm_session import verify_access_token

    assert verify_access_token("not-a-valid-jwt", "test-secret") is None


def test_access_token_without_user_id_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-123", "session-123", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload.pop("sub")
    modified_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(modified_token, secret) is None


def test_access_token_without_session_id_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-123", "session-123", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload.pop("sid")
    modified_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(modified_token, secret) is None


def test_access_token_without_token_id_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-123", "session-123", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload.pop("jti")
    modified_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(modified_token, secret) is None



def test_expired_refresh_token_rejected(monkeypatch):
    from datetime import timedelta

    import modules.m_auth.m_auth_sm_session as session

    secret = "test-secret-key-that-is-at-least-32-bytes"

    tokens = session.create_session_tokens(
        user_id="user-expiry",
        session_id="session-expiry",
        secret_key=secret,
    )

    refresh_token = (
        tokens["refresh_token"]
        if isinstance(tokens, dict)
        else tokens[1]
    )

    real_datetime = session.datetime

    class FutureDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.now(tz) + timedelta(days=8)

    monkeypatch.setattr(session, "datetime", FutureDateTime)

    assert session.refresh_session(refresh_token, secret) is None


def test_access_token_rejects_missing_required_inputs():
    import pytest

    from modules.m_auth.m_auth_sm_session import create_access_token

    with pytest.raises(ValueError):
        create_access_token("", "session-1", "secret")

    with pytest.raises(ValueError):
        create_access_token("user-1", "session-1", "secret", expires_minutes=-1)


def test_access_token_verification_rejects_missing_inputs():
    from modules.m_auth.m_auth_sm_session import verify_access_token

    assert verify_access_token("", "secret") is None
    assert verify_access_token("some-token", "") is None


def test_access_token_with_wrong_type_rejected():
    import jwt

    from modules.m_auth.m_auth_sm_session import (
        create_access_token,
        verify_access_token,
    )

    secret = "test-secret-key-that-is-at-least-32-bytes"
    token = create_access_token("user-1", "session-1", secret)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload["type"] = "refresh"
    wrong_token = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_access_token(wrong_token, secret) is None


def test_refresh_token_verification_rejects_missing_inputs():
    from modules.m_auth.m_auth_sm_session import verify_refresh_token

    assert verify_refresh_token("", "some-hash") is False
    assert verify_refresh_token("some-token", "") is False


def test_register_refresh_token_rejects_missing_inputs():
    import pytest

    from modules.m_auth.m_auth_sm_session import register_refresh_token

    with pytest.raises(ValueError):
        register_refresh_token("", "user-1", "session-1")

    with pytest.raises(ValueError):
        register_refresh_token("token-1", "user-1", "session-1", expires_days=-1)


def test_create_session_tokens_rejects_revoked_session():
    import pytest

    import modules.m_auth.m_auth_sm_session as session

    session_id = "revoked-create-test"
    session._REVOKED_SESSIONS.add(session_id)

    with pytest.raises(ValueError):
        session.create_session_tokens(
            "user-1",
            session_id,
            "test-secret-key-that-is-at-least-32-bytes",
        )


def test_refresh_session_rejects_missing_inputs():
    import modules.m_auth.m_auth_sm_session as session

    assert session.refresh_session("", "secret") is None
    assert session.refresh_session("some-token", "") is None


def test_refresh_session_rejects_revoked_session():
    import modules.m_auth.m_auth_sm_session as session

    secret = "test-secret-key-that-is-at-least-32-bytes"
    session_id = "revoked-refresh-test"

    tokens = session.create_session_tokens("user-1", session_id, secret)
    refresh_token = (
        tokens["refresh_token"] if isinstance(tokens, dict) else tokens[1]
    )

    session._REVOKED_SESSIONS.add(session_id)

    assert session.refresh_session(refresh_token, secret) is None


def test_revoke_refresh_token_rejects_missing_or_already_revoked():
    import modules.m_auth.m_auth_sm_session as session

    assert session.revoke_refresh_token("") is False
    assert session.revoke_refresh_token("unknown-token") is False

    secret = "test-secret-key-that-is-at-least-32-bytes"
    tokens = session.create_session_tokens("user-1", "revoke-test", secret)
    refresh_token = (
        tokens["refresh_token"] if isinstance(tokens, dict) else tokens[1]
    )

    assert session.revoke_refresh_token(refresh_token) is True
    assert session.revoke_refresh_token(refresh_token) is False


def test_revoke_session_rejects_missing_session_id():
    import modules.m_auth.m_auth_sm_session as session

    assert session.revoke_session("") is False
