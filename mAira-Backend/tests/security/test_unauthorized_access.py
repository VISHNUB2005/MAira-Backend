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
