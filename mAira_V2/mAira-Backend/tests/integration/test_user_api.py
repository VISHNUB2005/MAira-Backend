"""Integration tests for User profile API."""

import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_get_user_profile(
    client: AsyncClient, test_student_user: User, student_auth_headers: dict
):
    res = await client.get("/api/v1/users/me", headers=student_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == test_student_user.user_id
    assert data["email"] == test_student_user.email
    assert data["user_type"] == test_student_user.user_type


@pytest.mark.asyncio
async def test_unauthenticated_profile_rejected(client: AsyncClient):
    res = await client.get("/api/v1/users/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_admin_profile(
    client: AsyncClient, admin_auth_headers: dict
):
    res = await client.get("/api/v1/users/me", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test.admin@example.com"
    assert data["user_type"] == "ADMIN"
