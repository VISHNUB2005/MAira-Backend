"""Integration tests for registration, two-step MFA, login, refresh, and logout flows."""

import re
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.email_service import MockEmailProvider

settings = get_settings()


@pytest.mark.asyncio
async def test_full_registration_ticket_lifecycle_and_replay_protection(client: AsyncClient, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    test_email = "new.student@institution.edu"

    # 1. Pre-approve the user in the database with NULL password
    await user_repo.create_user(email=test_email, user_type="STUDENT", status="ACTIVE")

    # 2. Initiate registration
    init_res = await client.post(
        "/api/v1/auth/register/initiate",
        json={"email": test_email},
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["email"] == test_email
    assert init_data["expires_in_seconds"] == 300

    # 3. Verify email was dispatched to mock outbox
    msg = MockEmailProvider.get_latest_for(test_email)
    assert msg is not None
    assert "Registration Verification Code" in msg["subject"]
    match = re.search(r"\b\d{6}\b", msg["text"])
    assert match is not None
    otp_code = match.group(0)

    # 4. Bad OTP attempt
    bad_otp_res = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": test_email, "otp": "000000"},
    )
    assert bad_otp_res.status_code == 400

    # 5. Correct OTP -> returns ticket bound to otp_id
    verify_res = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": test_email, "otp": otp_code},
    )
    assert verify_res.status_code == 200
    ticket = verify_res.json()["registration_ticket"]
    assert ticket is not None

    # 6. Set password (canonical endpoint)
    complete_res = await client.post(
        "/api/v1/auth/register/set-password",
        json={
            "registration_ticket": ticket,
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )
    assert complete_res.status_code == 200
    assert "registration completed" in complete_res.json()["message"].lower()

    # 7. CRITICAL SECURITY TEST: Registration Ticket Replay Attack
    # Replaying the exact same ticket must be rejected!
    replay_ticket_res = await client.post(
        "/api/v1/auth/register/set-password",
        json={
            "registration_ticket": ticket,
            "password": "AttackerOverridingPassword123!",
            "confirm_password": "AttackerOverridingPassword123!",
        },
    )
    assert replay_ticket_res.status_code in (401, 409)

    # 8. Re-initiate registration on already-registered account must be rejected with 409
    re_init_res = await client.post(
        "/api/v1/auth/register/initiate",
        json={"email": test_email},
    )
    assert re_init_res.status_code == 409


@pytest.mark.asyncio
async def test_two_step_mfa_login_and_session_lifecycle(client: AsyncClient, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    email = "mfa.student@institution.edu"
    from app.core.security import hash_password

    user = await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    # Ensure MFA is active
    settings.MFA_ENABLED = True

    # Step 1: Login with credentials -> expect MFA challenge
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data.get("mfa_required") is True
    assert "mfa_token" in login_data
    mfa_token = login_data["mfa_token"]

    # Retrieve MFA code from mock outbox
    msg = MockEmailProvider.get_latest_for(email)
    assert msg is not None
    assert "Login Verification Code" in msg["subject"]
    match = re.search(r"\b\d{6}\b", msg["text"])
    assert match is not None
    mfa_code = match.group(0)

    # Step 2: Bad MFA code attempt -> rejected
    bad_mfa_res = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": "000000"},
    )
    assert bad_mfa_res.status_code == 400

    # Step 2: Correct MFA code -> returns authenticated session tokens
    verify_mfa_res = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": mfa_code},
    )
    assert verify_mfa_res.status_code == 200
    session_data = verify_mfa_res.json()
    assert "access_token" in session_data
    assert "refresh_token" in session_data
    access_token = session_data["access_token"]
    refresh_token = session_data["refresh_token"]

    # Replay of already consumed MFA code -> rejected
    replay_mfa_res = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": mfa_code},
    )
    assert replay_mfa_res.status_code in (400, 401)

    # Step 3: Refresh session
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    new_access_token = new_tokens["access_token"]
    new_refresh_token = new_tokens["refresh_token"]
    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    # Step 4: Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
        json={"all_sessions": False},
    )
    assert logout_res.status_code == 200

    # Step 5: Presenting defunct old refresh token -> Rejected
    old_token_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert old_token_res.status_code == 401
    assert "invalid or expired" in old_token_res.json()["message"].lower()

    # Step 6: Presenting revoked refresh token -> Reuse / theft detection triggers
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh_token},
    )
    assert reuse_res.status_code == 401
    assert "compromised" in reuse_res.json()["message"].lower()



@pytest.mark.asyncio
async def test_unapproved_email_registration_rejected(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register/initiate",
        json={"email": "random.unapproved@domain.com"},
    )
    assert res.status_code == 404
    assert "not authorized" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_invalid_password_fails_with_dummy_verification(client: AsyncClient, test_student_user: User):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": test_student_user.email, "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_unknown_email_returns_identical_generic_error(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent.student@institution.edu", "password": "AnyPassword123!"},
    )
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(client: AsyncClient, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.create_user("inactive.user@test.com", user_type="STUDENT", status="INACTIVE")
    from app.core.security import hash_password
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive.user@test.com", "password": "ValidPassword123!"},
    )
    assert res.status_code == 403
    assert "inactive" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_all_sessions_revokes_all_active_sessions(client: AsyncClient, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    email = "multisession.student@institution.edu"
    from app.core.security import hash_password

    user = await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    # Session 1 login
    login1 = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword123!"})
    mfa1 = login1.json()["mfa_token"]
    msg1 = MockEmailProvider.get_latest_for(email)
    code1 = re.search(r"\b\d{6}\b", msg1["text"]).group(0)
    tokens1 = (await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa1, "code": code1})).json()

    # Session 2 login
    login2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword123!"})
    mfa2 = login2.json()["mfa_token"]
    msg2 = MockEmailProvider.get_latest_for(email)
    code2 = re.search(r"\b\d{6}\b", msg2["text"]).group(0)
    tokens2 = (await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa2, "code": code2})).json()

    # Both sessions work initially
    me1 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens1['access_token']}"})
    assert me1.status_code == 200
    me2 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens2['access_token']}"})
    assert me2.status_code == 200

    # Logout all sessions using Session 1
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens1['access_token']}"},
        json={"all_sessions": True},
    )
    assert logout_res.status_code == 200

    # Both sessions must now be rejected
    after1 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens1['access_token']}"})
    assert after1.status_code == 401
    after2 = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens2['access_token']}"})
    assert after2.status_code == 401


@pytest.mark.asyncio
async def test_account_deactivation_blocks_active_session(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
):
    user_repo = UserRepository(db_session)
    email = "to.be.deactivated@institution.edu"
    from app.core.security import hash_password

    user = await user_repo.create_user(email=email, user_type="STUDENT", status="ACTIVE")
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()
    target_user_id = user.user_id

    # Student logs in
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword123!"})
    mfa_token = login_res.json()["mfa_token"]
    msg = MockEmailProvider.get_latest_for(email)
    code = re.search(r"\b\d{6}\b", msg["text"]).group(0)
    tokens = (await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})).json()
    access_token = tokens["access_token"]

    # Student can access profile
    ok_res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert ok_res.status_code == 200

    # Admin deactivates student
    deact_res = await client.patch(
        f"/api/v1/admin/users/students/{target_user_id}/status",
        json={"status": "INACTIVE"},
        headers=admin_auth_headers,
    )
    assert deact_res.status_code == 200

    # Student tries to use previously valid token -> Rejected (session revoked / account inactive)
    blocked_res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert blocked_res.status_code in (401, 403)
    assert any(
        msg in blocked_res.json()["message"].lower()
        for msg in ("inactive", "revoked")
    )

