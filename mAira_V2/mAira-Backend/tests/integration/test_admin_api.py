"""Integration tests for administrator user management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_admin_student_management_lifecycle(
    client: AsyncClient, admin_auth_headers: dict
):
    target_email = "admitted.student2026@institution.edu"

    # 1. Admin creates student via canonical route
    create_res = await client.post(
        "/api/v1/admin/users/students",
        json={"email": target_email, "name": "Admitted Student", "user_type": "STUDENT"},
        headers=admin_auth_headers,
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["email"] == target_email
    assert created_data["status"] == "ACTIVE"
    assert created_data["password_set"] is False
    target_user_id = created_data["user_id"]

    # 2. Duplicate student creation fails with 409
    dup_res = await client.post(
        "/api/v1/admin/users/students",
        json={"email": target_email},
        headers=admin_auth_headers,
    )
    assert dup_res.status_code == 409

    # 3. View single student
    get_res = await client.get(
        f"/api/v1/admin/users/students/{target_user_id}",
        headers=admin_auth_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["user_id"] == target_user_id

    # 4. Deactivate student
    deact_res = await client.patch(
        f"/api/v1/admin/users/students/{target_user_id}/status",
        json={"status": "INACTIVE"},
        headers=admin_auth_headers,
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "INACTIVE"

    # 5. Check analytics reflects changes
    summary_res = await client.get(
        "/api/v1/admin/users/analytics",
        headers=admin_auth_headers,
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["total_students"] >= 1
    assert summary_data["inactive_students"] >= 1

    # 6. Delete student
    del_res = await client.delete(
        f"/api/v1/admin/users/students/{target_user_id}",
        headers=admin_auth_headers,
    )
    assert del_res.status_code == 200

    # 7. Verifying deletion
    get_after_del = await client.get(
        f"/api/v1/admin/users/students/{target_user_id}",
        headers=admin_auth_headers,
    )
    assert get_after_del.status_code == 404


@pytest.mark.asyncio
async def test_student_forbidden_from_admin_api(
    client: AsyncClient, student_auth_headers: dict
):
    """Verify standard students cannot access admin operations."""
    res = await client.post(
        "/api/v1/admin/users/students",
        json={"email": "hacked@institution.edu"},
        headers=student_auth_headers,
    )
    assert res.status_code == 403
