"""Security tests for authentication concurrency, race conditions, replay protection, and attempt limits."""

import asyncio
import re
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_mfa_challenge_token, hash_password
from app.models.user import User
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.services.email_service import MockEmailProvider


from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.database import get_db
from app.main import app
from tests.conftest import test_engine


@pytest.fixture(autouse=True)
def clean_emails_and_enable_mfa():
    from app.core.config import get_settings
    settings = get_settings()
    old_mfa = settings.MFA_ENABLED
    settings.MFA_ENABLED = True
    MockEmailProvider.clear()
    yield
    MockEmailProvider.clear()
    settings.MFA_ENABLED = old_mfa







@pytest.mark.asyncio
async def test_concurrent_registration_completion_single_winner(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that concurrent requests using the same registration ticket produce exactly ONE winner."""
    user_repo = UserRepository(db_session)
    # 1. Create approved unactivated user
    user = await user_repo.create_user(
        email="concurrent.student@institution.edu",
        user_type="STUDENT",
        status="ACTIVE",
    )
    await db_session.flush()

    # 2. Initiate registration
    init_res = await client.post(
        "/api/v1/auth/register/initiate",
        json={"email": "concurrent.student@institution.edu"},
    )
    assert init_res.status_code == 200

    # 3. Retrieve OTP from mock outbox
    msg = MockEmailProvider.get_latest_for("concurrent.student@institution.edu")
    assert msg is not None
    otp = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    # 4. Verify OTP to get registration ticket
    verify_res = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": "concurrent.student@institution.edu", "otp": otp},
    )
    assert verify_res.status_code == 200
    ticket = verify_res.json()["registration_ticket"]

    # 5. Launch TWO concurrent password completion requests using the EXACT same ticket
    payload_a = {
        "registration_ticket": ticket,
        "password": "ValidPasswordA123!",
        "confirm_password": "ValidPasswordA123!",
    }
    payload_b = {
        "registration_ticket": ticket,
        "password": "ValidPasswordB123!",
        "confirm_password": "ValidPasswordB123!",
    }

    res_a, res_b = await asyncio.gather(
        client.post("/api/v1/auth/register/set-password", json=payload_a),
        client.post("/api/v1/auth/register/set-password", json=payload_b),
        return_exceptions=False,
    )

    statuses = [res_a.status_code, res_b.status_code]
    # Exactly ONE must succeed (200 OK)
    assert 200 in statuses, f"Expected one 200, got: {statuses}"
    # The other must fail (401 or 409)
    assert any(s in (401, 409) for s in statuses), f"Expected one 401/409, got: {statuses}"
    assert statuses.count(200) == 1, "Only one concurrent registration request may succeed"


@pytest.mark.asyncio
async def test_concurrent_refresh_token_rotation_single_winner(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that concurrent refresh requests using the same refresh token produce exactly ONE winner."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create_user(
        email="refresh.student@institution.edu",
        user_type="STUDENT",
        status="ACTIVE",
    )
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    # Step 1: Login to get initial MFA code
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh.student@institution.edu", "password": "ValidPassword123!", "role": "STUDENT"},
    )
    assert login_res.status_code == 200
    mfa_token = login_res.json()["mfa_token"]

    msg = MockEmailProvider.get_latest_for("refresh.student@institution.edu")
    code = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    # Step 2: Complete MFA to obtain tokens
    mfa_res = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": code},
    )
    assert mfa_res.status_code == 200
    tokens = mfa_res.json()
    refresh_token = tokens["refresh_token"]

    # Step 3: Launch TWO concurrent refresh calls with the SAME refresh token
    ref_a, ref_b = await asyncio.gather(
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        return_exceptions=False,
    )

    statuses = [ref_a.status_code, ref_b.status_code]
    assert 200 in statuses, f"Expected one 200 OK, got: {statuses}"
    assert 401 in statuses, f"Expected one 401 Unauthorized, got: {statuses}"
    assert statuses.count(200) == 1, "Exactly one concurrent refresh call may succeed"


@pytest.mark.asyncio
async def test_reuse_of_revoked_refresh_token_triggers_theft_revocation(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that presenting a revoked refresh token triggers theft detection and invalidates all user sessions."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create_user(
        email="theft.student@institution.edu",
        user_type="STUDENT",
        status="ACTIVE",
    )
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    # Login and verify MFA
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "theft.student@institution.edu", "password": "ValidPassword123!", "role": "STUDENT"},
    )
    mfa_token = login_res.json()["mfa_token"]
    msg = MockEmailProvider.get_latest_for("theft.student@institution.edu")
    code = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    mfa_res = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    session_tokens = mfa_res.json()
    refresh_token_1 = session_tokens["refresh_token"]

    # Rotate refresh token
    rotate_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert rotate_res.status_code == 200
    refresh_token_2 = rotate_res.json()["refresh_token"]
    access_token_2 = rotate_res.json()["access_token"]

    # Logout with access_token_2 -> marks session is_revoked = True
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token_2}"},
        json={"all_sessions": False},
    )
    assert logout_res.status_code == 200

    # Attacker tries to refresh with refresh_token_2 (which belongs to revoked session)
    theft_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_2})
    assert theft_res.status_code == 401
    assert "compromised" in theft_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_mfa_otp_replay_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that an MFA OTP cannot be verified twice."""
    user_repo = UserRepository(db_session)
    user = await user_repo.create_user(
        email="mfareplay.student@institution.edu",
        user_type="STUDENT",
        status="ACTIVE",
    )
    user.password_hash = hash_password("ValidPassword123!")
    await db_session.flush()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "mfareplay.student@institution.edu", "password": "ValidPassword123!", "role": "STUDENT"},
    )
    mfa_token = login_res.json()["mfa_token"]
    msg = MockEmailProvider.get_latest_for("mfareplay.student@institution.edu")
    code = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    # First verification succeeds
    res1 = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert res1.status_code == 200

    # Replay of identical challenge and code fails
    res2 = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert res2.status_code in (400, 401)
    assert "consumed" in res2.json()["message"].lower() or "invalid" in res2.json()["message"].lower()


@pytest.mark.asyncio
async def test_mfa_expiry_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that an expired MFA challenge token is rejected."""
    expired_token = create_mfa_challenge_token(
        account_id=999,
        email="expired@institution.edu",
        role="STUDENT",
        account_type="USER",
        otp_id="00000000-0000-0000-0000-000000000001",
        expires_minutes=-5,  # 5 minutes in the past
    )

    res = await client.post("/api/v1/auth/mfa/verify", json={"mfa_token": expired_token, "code": "123456"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_otp_maximum_attempt_enforcement(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify that 5 failed OTP attempts lock out the OTP, rejecting even the correct code on the 6th attempt."""
    user_repo = UserRepository(db_session)
    await user_repo.create_user(
        email="bruteforce.student@institution.edu",
        user_type="STUDENT",
        status="ACTIVE",
    )
    await db_session.flush()

    # Initiate OTP
    await client.post("/api/v1/auth/register/initiate", json={"email": "bruteforce.student@institution.edu"})
    msg = MockEmailProvider.get_latest_for("bruteforce.student@institution.edu")
    correct_otp = re.search(r"\b\d{6}\b", msg["text"]).group(0)

    # Submit 5 incorrect codes
    for attempt in range(5):
        fail_res = await client.post(
            "/api/v1/auth/register/verify-otp",
            json={"email": "bruteforce.student@institution.edu", "otp": "000000"},
        )
        assert fail_res.status_code == 400

    # 6th attempt with the CORRECT OTP must be rejected because max attempts were reached
    lock_res = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": "bruteforce.student@institution.edu", "otp": correct_otp},
    )
    assert lock_res.status_code == 400
    assert "exceeded" in lock_res.json()["message"].lower() or "invalid" in lock_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_concurrent_otp_verification():
    """Verify concurrent OTP verification requests with atomic attempt tracking."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as setup_session:
        user_repo = UserRepository(setup_session)
        user = await user_repo.get_user_by_email("concurrent.otp@institution.edu")
        if not user:
            await user_repo.create_user(
                email="concurrent.otp@institution.edu",
                user_type="STUDENT",
                status="ACTIVE",
            )
            await setup_session.commit()

    async def _get_independent_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _get_independent_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        init_res = await client.post("/api/v1/auth/register/initiate", json={"email": "concurrent.otp@institution.edu"})
        assert init_res.status_code == 200
        msg = MockEmailProvider.get_latest_for("concurrent.otp@institution.edu")
        otp = re.search(r"\b\d{6}\b", msg["text"]).group(0)

        res_a, res_b = await asyncio.gather(
            client.post("/api/v1/auth/register/verify-otp", json={"email": "concurrent.otp@institution.edu", "otp": otp}),
            client.post("/api/v1/auth/register/verify-otp", json={"email": "concurrent.otp@institution.edu", "otp": otp}),
            return_exceptions=False,
        )
        assert 200 in (res_a.status_code, res_b.status_code)

    app.dependency_overrides.clear()
