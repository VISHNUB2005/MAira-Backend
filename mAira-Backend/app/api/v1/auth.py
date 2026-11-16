"""Authentication and Session Management API Endpoints."""

from typing import Union
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthenticatedAccount, get_current_account, get_db
from app.core.config import get_settings
from app.schemas.auth import (
    LoginMFAChallengeResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MFAVerifyRequest,
    RegisterCompletePasswordRequest,
    RegisterInitiateRequest,
    RegisterInitiateResponse,
    RegisterVerifyOtpRequest,
    RegisterVerifyOtpResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.schemas.common import MessageOnlyResponse
from app.security.rate_limiter import get_client_ip, rate_limiter
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Registration"])
settings = get_settings()


# ==============================================================================
# 1. REGISTRATION WORKFLOW (Admin-controlled allowlist)
# ==============================================================================

@router.post(
    "/register/initiate",
    response_model=RegisterInitiateResponse,
    summary="Initiate registration for pre-approved institutional email",
)
async def register_initiate(
    payload: RegisterInitiateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Step 1: Check if email exists in database allowlist and dispatch verification OTP."""
    ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        key=f"otp_req:{ip}",
        max_requests=settings.RATE_LIMIT_OTP_MAX,
        window_seconds=settings.RATE_LIMIT_OTP_WINDOW_SECONDS,
    )

    auth_service = AuthService(session)
    expires_in_seconds = await auth_service.initiate_registration(str(payload.email))

    return RegisterInitiateResponse(
        message="Verification code sent to institutional email address.",
        email=str(payload.email),
        expires_in_seconds=expires_in_seconds,
    )


@router.post(
    "/register/verify-otp",
    response_model=RegisterVerifyOtpResponse,
    summary="Verify registration OTP and obtain registration ticket",
)
async def register_verify_otp(
    payload: RegisterVerifyOtpRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Step 2: Submit and verify numeric OTP; returns a short-lived signed registration ticket bound to otp_id."""
    ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        key=f"otp_verify:{ip}",
        max_requests=10,
        window_seconds=60,
    )

    auth_service = AuthService(session)
    ticket = await auth_service.verify_registration_otp(
        email=str(payload.email),
        code=payload.otp,
    )

    return RegisterVerifyOtpResponse(
        message="Verification successful. Please create your password.",
        registration_ticket=ticket,
        expires_in_minutes=settings.REGISTRATION_TICKET_EXPIRE_MINUTES,
    )


@router.post(
    "/register/set-password",
    response_model=MessageOnlyResponse,
    summary="Complete registration by setting account password",
)
@router.post(
    "/register/complete-password",
    response_model=MessageOnlyResponse,
    include_in_schema=False,
    summary="Legacy alias for set-password",
)
async def register_set_password(
    payload: RegisterCompletePasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Step 3: Atomically verify ticket, consume OTP, and set password."""
    auth_service = AuthService(session)
    await auth_service.complete_registration(
        ticket=payload.registration_ticket,
        password=payload.password,
        confirm_password=payload.confirm_password,
    )

    return MessageOnlyResponse(
        message="Account registration completed successfully. You may now log in."
    )


# ==============================================================================
# 2. LOGIN & TWO-STEP MFA WORKFLOW
# ==============================================================================

@router.post(
    "/login",
    response_model=Union[LoginResponse, LoginMFAChallengeResponse],
    summary="Authenticate with email and password",
)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Step 1: Verify credentials; return MFA challenge if enabled or full session tokens."""
    ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        key=f"login:{ip}",
        max_requests=settings.RATE_LIMIT_LOGIN_MAX,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )

    auth_service = AuthService(session)
    return await auth_service.login(
        email=str(payload.email),
        plain_password=payload.password,
    )


@router.post(
    "/mfa/verify",
    response_model=LoginResponse,
    summary="Verify MFA challenge code to establish session",
)
async def verify_mfa(
    payload: MFAVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Step 2: Submit MFA challenge token and 6-digit code to complete login."""
    ip = get_client_ip(request)
    rate_limiter.check_rate_limit(
        key=f"mfa_verify:{ip}",
        max_requests=10,
        window_seconds=60,
    )

    auth_service = AuthService(session)
    return await auth_service.verify_mfa(
        mfa_token=payload.mfa_token,
        code=payload.code,
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Rotate refresh token and issue new token pair",
)
async def refresh_tokens(
    payload: TokenRefreshRequest,
    session: AsyncSession = Depends(get_db),
):
    """Validate refresh token hash in tb_con_user_sessions and rotate atomically."""
    auth_service = AuthService(session)
    return await auth_service.refresh_session(payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageOnlyResponse,
    summary="Revoke current authentication session or all sessions",
)
async def logout(
    payload: LogoutRequest = LogoutRequest(),
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_db),
):
    """Revoke session (or all active sessions) and refresh token in database."""
    auth_service = AuthService(session)
    await auth_service.logout(
        session_id=account.session_id,
        account_id=account.account_id,
        account_type=account.account_type,
        all_sessions=payload.all_sessions,
    )

    return MessageOnlyResponse(
        message="Successfully logged out of all active sessions." if payload.all_sessions else "Successfully logged out."
    )
