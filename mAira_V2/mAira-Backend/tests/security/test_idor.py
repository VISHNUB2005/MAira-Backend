"""Security tests for Insecure Direct Object References (IDOR) and Privilege Escalation."""

from datetime import datetime, timedelta, timezone
import secrets
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, hash_refresh_token
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_cross_user_conversation_access_forbidden(
    client: AsyncClient, db_session: AsyncSession, student_auth_headers: dict
):
    """Verify User B cannot view, message, or delete User A's conversation."""
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    # 1. Student A creates a conversation
    res_a = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Student A Private Project"},
        headers=student_auth_headers,
    )
    assert res_a.status_code == 201
    conv_id = res_a.json()["chat_session_id"]

    # 2. Setup Student B
    user_b = await user_repo.create_user(
        email="student.b@example.com", user_type="STUDENT", status="ACTIVE"
    )
    user_b.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    raw_token_b = secrets.token_urlsafe(64)
    session_b = await session_repo.create_session(
        account_type="USER",
        account_id=user_b.user_id,
        refresh_token_hash=hash_refresh_token(raw_token_b),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    jwt_b = create_access_token(
        user_id=user_b.user_id,
        session_id=str(session_b.session_id),
        email=user_b.email,
        role="STUDENT",
        account_type="USER",
    )
    headers_b = {"Authorization": f"Bearer {jwt_b}"}

    # 3. Student B attempts to access Student A's conversation -> Rejected (404/403)
    idor_get = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=headers_b,
    )
    assert idor_get.status_code in (403, 404)

    # 4. Student B attempts to post message to Student A's conversation -> Rejected
    idor_post = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "Malicious prompt injection"},
        headers=headers_b,
    )
    assert idor_post.status_code in (403, 404)

    # 5. Student B attempts to delete Student A's conversation -> Rejected
    idor_del = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=headers_b,
    )
    assert idor_del.status_code in (403, 404)


@pytest.mark.asyncio
async def test_privilege_escalation_student_to_admin_rejected(
    client: AsyncClient, student_auth_headers: dict
):
    """Verify normal student cannot access any admin endpoint."""
    res1 = await client.get("/api/v1/admin/users/", headers=student_auth_headers)
    assert res1.status_code == 403

    res2 = await client.get("/api/v1/admin/users/analytics/summary", headers=student_auth_headers)
    assert res2.status_code == 403

    res3 = await client.delete("/api/v1/admin/users/1", headers=student_auth_headers)
    assert res3.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_create_chat(
    client: AsyncClient, admin_auth_headers: dict
):
    """Verify administrator cannot access chat/AI features per Group 6 RBAC policy."""
    res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Admin attempting chat"},
        headers=admin_auth_headers,
    )
    assert res.status_code == 403
