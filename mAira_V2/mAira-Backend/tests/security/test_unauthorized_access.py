"""Security tests for unauthorized and unauthenticated API access."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_protected_routes_reject_missing_token(client: AsyncClient):
    # Chat endpoints
    res1 = await client.get("/api/v1/chat/conversations")
    assert res1.status_code == 401

    res2 = await client.post("/api/v1/chat/conversations", json={"title": "Unauthorized"})
    assert res2.status_code == 401

    # User profile
    res3 = await client.get("/api/v1/users/me")
    assert res3.status_code == 401

    # Admin endpoints
    res4 = await client.get("/api/v1/admin/users/")
    assert res4.status_code == 401


@pytest.mark.asyncio
async def test_protected_routes_reject_invalid_token(client: AsyncClient):
    bad_headers = {"Authorization": "Bearer invalid.jwt.token"}
    res = await client.get("/api/v1/users/me", headers=bad_headers)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_routes_reject_malformed_auth_header(client: AsyncClient):
    bad_headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    res = await client.get("/api/v1/users/me", headers=bad_headers)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_routes_reject_token_type_mismatch(client: AsyncClient):
    from app.core.security import create_mfa_challenge_token, create_registration_ticket

    # 1. Registration ticket presented as Bearer token
    reg_ticket = create_registration_ticket(email="test@institution.edu", user_id=1, otp_id="otp-123")
    res1 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {reg_ticket}"})
    assert res1.status_code == 401
    assert "invalid or expired access token" in res1.json()["message"].lower()

    # 2. MFA challenge token presented as Bearer token
    mfa_token = create_mfa_challenge_token(
        account_id=1,
        email="test@institution.edu",
        role="STUDENT",
        account_type="USER",
        otp_id="otp-456",
    )
    res2 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {mfa_token}"})
    assert res2.status_code == 401
    assert "invalid or expired access token" in res2.json()["message"].lower()
