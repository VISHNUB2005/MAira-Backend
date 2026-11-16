
import pytest
from fastapi.testclient import TestClient

from main import app
from modules.m_auth.m_auth_sm_session import (
    create_access_token,
    get_jwt_secret_key,
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def generate_token(role: str) -> str:
    return create_access_token(
        user_id=f"test-{role.lower()}-001",
        session_id=f"session-{role.lower()}-001",
        secret_key=get_jwt_secret_key(),
        role=role,
    )


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_missing_token_returns_401(client):
    response = client.get("/api/v1/protected/test")

    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/protected/test",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_user_can_access_user_dashboard(client):
    token = generate_token("USER")

    response = client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "USER"


def test_admin_can_access_admin_dashboard(client):
    token = generate_token("ADMIN")

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_user_cannot_access_admin_dashboard(client):
    token = generate_token("USER")

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
