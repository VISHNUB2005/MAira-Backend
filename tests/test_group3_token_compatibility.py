import base64
import hashlib
import hmac
import json
import time

from modules.m_auth.m_auth_registration_token import RegistrationTokenVerifier


def generate_group3_style_token(secret, payload):
    payload_bytes = json.dumps(payload).encode("utf-8")
    payload_part = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

    signature = hmac.new(
        secret.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload_part}.{signature}"


def test_accepts_group3_compatible_registration_token(monkeypatch):
    secret = "test-shared-secret"
    monkeypatch.setenv("MAIRA_AUTH_SECRET_KEY", secret)

    verifier = RegistrationTokenVerifier()

    payload = {
        "sub": "test@example.com",
        "email": "test@example.com",
        "flow": "registration",
        "stage": "step_3_password_setup",
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "jti": "test-registration-token-123",
    }

    token = generate_group3_style_token(secret, payload)

    claims = verifier.verify_registration_token(token)
    assert claims is not None
    assert claims["email"] == "test@example.com"
    assert claims["jti"] == "test-registration-token-123"
    assert claims["exp"] == payload["exp"]


def test_rejects_expired_registration_token(monkeypatch):
    secret = "test-shared-secret"
    monkeypatch.setenv("MAIRA_AUTH_SECRET_KEY", secret)

    verifier = RegistrationTokenVerifier()

    payload = {
        "sub": "test@example.com",
        "email": "test@example.com",
        "flow": "registration",
        "stage": "step_3_password_setup",
        "iat": int(time.time()) - 1000,
        "exp": int(time.time()) - 100,
        "jti": "expired-token-123",
    }

    token = generate_group3_style_token(secret, payload)

    assert verifier.verify_registration_token(token) is None


def test_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("MAIRA_AUTH_SECRET_KEY", "test-shared-secret")

    verifier = RegistrationTokenVerifier()

    assert verifier.verify_registration_token("invalid.payload") is None
