import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.m_auth.m_auth_password_routes import router
from modules.m_auth.m_auth_password_setup import PasswordSetupService


class FakeTokenService:
    def verify_registration_token(self, token):
        if token != "valid-token":
            return None

        return {
            "email": "student@example.com",
            "jti": "route-test-jti",
            "exp": time.time() + 900,
        }


class FakeUserRepository:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.saved_hash = None
        self.saved_email = None
        self.saved_jti = None
        self.saved_expiry = None

    def complete_password_setup(self, email, password_hash, jti, expires_at):
        self.saved_email = email
        self.saved_hash = password_hash
        self.saved_jti = jti
        self.saved_expiry = expires_at
        return self.allowed


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.state.password_setup_service = PasswordSetupService(
        FakeTokenService(),
        FakeUserRepository(),
    )
    return TestClient(app)


def test_password_setup_success(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "valid-token",
            "password": "StrongPassword@123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password setup completed successfully."
    }
    assert "password_hash" not in response.text


def test_invalid_token(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "invalid-token",
            "password": "StrongPassword@123",
        },
    )
    assert response.status_code == 400


def test_missing_password(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={"registration_token": "valid-token"},
    )
    assert response.status_code == 422


def test_missing_token(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={"password": "StrongPassword@123"},
    )
    assert response.status_code == 422


def test_service_not_configured():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "valid-token",
            "password": "StrongPassword@123",
        },
    )
    assert response.status_code == 503


def test_ineligible_account_returns_409():
    app = FastAPI()
    app.include_router(router)
    app.state.password_setup_service = PasswordSetupService(
        FakeTokenService(),
        FakeUserRepository(allowed=False),
    )

    response = TestClient(app).post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "valid-token",
            "password": "StrongPassword@123",
        },
    )

    assert response.status_code == 409
    assert "password_hash" not in response.text
    assert "StrongPassword@123" not in response.text


def test_empty_token_rejected(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "",
            "password": "StrongPassword@123",
        },
    )
    assert response.status_code == 422


def test_empty_password_rejected(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "valid-token",
            "password": "",
        },
    )
    assert response.status_code == 422


def test_excessively_long_password_rejected(client):
    response = client.post(
        "/api/v1/auth/password/setup",
        json={
            "registration_token": "valid-token",
            "password": "A" * 1025,
        },
    )
    assert response.status_code == 422
