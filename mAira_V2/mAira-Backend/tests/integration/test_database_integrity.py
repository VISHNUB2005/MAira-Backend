"""Database Integrity and Storage Security Verification Tests.

Verifies:
1. Refresh tokens are hashed with SHA-256 (64 hex characters) and never stored raw.
2. OTP values are hashed with SHA-256 and never stored in plain text.
3. OTP records are correctly marked consumed with used_at timestamp upon verification.
4. Chat messages are correctly associated with sessions via foreign key.
5. No passwords, raw tokens, or secrets appear in audit logs.
6. Multi-step transaction failure rolls back cleanly without leaving inconsistent state.
"""

import re
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.chat import ChatSession
from app.models.message import Message
from app.models.otp import OTPVerification
from app.models.session import UserSession
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.email_service import MockEmailProvider


@pytest.mark.asyncio
async def test_refresh_token_hashes_stored_not_raw(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that tb_con_user_sessions stores SHA-256 hashes, never raw refresh tokens."""
    user_repo = UserRepository(db_session)
    email = "db.integrity.refresh@institution.edu"

    user = await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword123!"})
    mfa_token = login_res.json()["mfa_token"]
    msg = MockEmailProvider.get_latest_for(email)
    code = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    verify_res = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert verify_res.status_code == 200
    tokens = verify_res.json()
    raw_refresh_token = tokens["refresh_token"]

    # Directly inspect tb_con_user_sessions in PostgreSQL
    result = await db_session.execute(
        select(UserSession).where(UserSession.account_id == user.user_id)
    )
    db_session_records = result.scalars().all()
    assert len(db_session_records) >= 1

    latest_session = db_session_records[-1]
    stored_hash = latest_session.refresh_token_hash

    # 1. Assert stored hash is 64 hex characters (SHA-256)
    assert len(stored_hash) == 64
    assert all(c in "0123456789abcdefABCDEF" for c in stored_hash)

    # 2. Assert raw refresh token is NOT in the database
    assert stored_hash != raw_refresh_token
    assert raw_refresh_token not in stored_hash


@pytest.mark.asyncio
async def test_otp_records_consumed_and_no_raw_otp_stored(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify OTP records are hashed, never plain text, and consumed upon verification."""
    user_repo = UserRepository(db_session)
    email = "db.integrity.otp@institution.edu"

    await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")
    await db_session.flush()

    # Initiate registration
    init_res = await client.post("/api/v1/auth/register/initiate", json={"email": email})
    assert init_res.status_code == 200

    msg = MockEmailProvider.get_latest_for(email)
    raw_otp = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    # Check OTP record before verification
    result = await db_session.execute(
        select(OTPVerification).where(OTPVerification.email == email)
    )
    otp_record = result.scalars().first()
    assert otp_record is not None
    assert otp_record.used_at is None

    # Assert raw 6-digit OTP is NEVER stored in database
    assert otp_record.otp_hash != raw_otp
    assert len(otp_record.otp_hash) == 64  # SHA-256 hex digest

    # Verify OTP -> returns ticket and sets verified_at
    verify_res = await client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": raw_otp})
    assert verify_res.status_code == 200
    ticket = verify_res.json()["registration_ticket"]

    # Expire session cache to read latest DB row
    await db_session.refresh(otp_record)
    assert otp_record.verified_at is not None
    assert otp_record.used_at is None  # Not used until password set

    # Complete registration (set password) -> consumes OTP and sets used_at
    complete_res = await client.post(
        "/api/v1/auth/register/set-password",
        json={
            "registration_ticket": ticket,
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )
    assert complete_res.status_code == 200

    # Refresh row to verify used_at is now set
    await db_session.refresh(otp_record)
    assert otp_record.used_at is not None


@pytest.mark.asyncio
async def test_audit_logs_never_contain_passwords_or_tokens(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that tb_con_audit_log contains no plain text credentials, tokens, or passwords."""
    result = await db_session.execute(select(AuditLog).limit(100))
    audit_logs = result.scalars().all()

    forbidden_keywords = ["password123", "secret", "bearer ", "mock_password"]

    for entry in audit_logs:
        details_str = str(entry.details).lower()
        action_str = entry.action.lower()

        for forbidden in forbidden_keywords:
            assert forbidden not in details_str, f"Forbidden keyword '{forbidden}' leaked in audit log {entry.audit_id}"
            assert forbidden not in action_str, f"Forbidden keyword '{forbidden}' leaked in audit action {entry.audit_id}"


@pytest.mark.asyncio
async def test_chat_messages_associated_with_session_and_cascades(
    client: AsyncClient, db_session: AsyncSession, student_auth_headers: dict
):
    """Verify messages are strictly bound to their chat_session_id."""
    res = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "DB Association Test"},
        headers=student_auth_headers,
    )
    session_id = res.json()["chat_session_id"]

    # Verify session row exists
    res_db = await db_session.execute(
        select(ChatSession).where(ChatSession.chat_session_id == session_id)
    )
    chat = res_db.scalars().first()
    assert chat is not None
    assert chat.is_deleted is False
