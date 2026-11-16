"""Authentication and Account Lifecycle Service."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AccountStatusError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    create_registration_ticket,
    decode_mfa_challenge_token,
    decode_registration_ticket,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.repositories.audit_repo import AuditRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginMFAChallengeResponse,
    LoginResponse,
    TokenRefreshResponse,
    UserSummary,
)
from app.services.otp_service import OTPService

settings = get_settings()


class AuthService:
    """Orchestrates registration, authentication, two-step MFA, tokens, and sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.audit_repo = AuditRepository(session)
        self.otp_service = OTPService(session)

    # ================= Account Identification =================
    async def identify_account(self, email: str) -> str:
        """Return REGISTER for an active account without a password, otherwise LOGIN.

        Unknown or inactive accounts are rejected with a generic authorization error.
        This endpoint intentionally returns no account identifiers or profile data.
        """
        clean_email = email.lower().strip()
        user = await self.user_repo.get_user_by_email(clean_email)
        if user:
            if user.status != "ACTIVE":
                raise NotFoundError("This email is not eligible. Contact your administrator.")
            return "REGISTER" if user.password_hash is None else "LOGIN"

        admin = await self.user_repo.get_admin_by_email(clean_email)
        if admin:
            if admin.status != "ACTIVE":
                raise NotFoundError("This email is not eligible. Contact your administrator.")
            return "REGISTER" if admin.password_hash is None else "LOGIN"

        raise NotFoundError("This email is not eligible. Contact your administrator.")

    # ================= Registration Flow =================
    async def initiate_registration(self, email: str) -> int:
        """Step 1: Check institutional allowlist in tb_con_user and dispatch OTP."""
        clean_email = email.lower().strip()
        user = await self.user_repo.get_user_by_email(clean_email)

        if not user:
            # Check tb_con_admin for initial admin registration if seeded
            admin = await self.user_repo.get_admin_by_email(clean_email)
            if not admin:
                raise NotFoundError("Email is not authorized for registration. Please contact your administrator.")
            if admin.password_hash is not None:
                raise ConflictError("Administrator account is already registered. Please proceed to login.")
            if admin.status != "ACTIVE":
                raise AccountStatusError(f"Account status is '{admin.status}'. Access denied.")
            expiry_sec, _ = await self.otp_service.initiate_registration_otp(clean_email, admin.admin_id)
            return expiry_sec

        if user.status != "ACTIVE":
            raise AccountStatusError(f"Account status is '{user.status}'. Registration cannot proceed.")

        if user.password_hash is not None:
            raise ConflictError("Account is already registered. Please proceed to login.")

        expiry_sec, _ = await self.otp_service.initiate_registration_otp(clean_email, user.user_id)
        return expiry_sec

    async def verify_registration_otp(self, email: str, code: str) -> str:
        """Step 2: Verify OTP and return a signed temporary registration ticket bound to otp_id."""
        clean_email = email.lower().strip()
        user = await self.user_repo.get_user_by_email(clean_email)
        admin = None
        account_id = None

        if user:
            account_id = user.user_id
        else:
            admin = await self.user_repo.get_admin_by_email(clean_email)
            if admin:
                account_id = admin.admin_id
            else:
                raise NotFoundError("Account not found.")

        # Verify OTP and obtain verified otp_id
        otp_id = await self.otp_service.verify_registration_otp(clean_email, code)

        # Issue short-lived ticket cryptographically bound to otp_id
        ticket = create_registration_ticket(clean_email, account_id, str(otp_id))
        return ticket

    async def complete_registration(
        self, ticket: str, password: str, confirm_password: str
    ) -> None:
        """Step 3: Atomically verify ticket, consume OTP, hash with bcrypt, and update DB.

        Guarantees single-use ticket protection and prevents concurrent replay attacks.
        """
        if password != confirm_password:
            raise ValidationError("Password and confirmation password do not match.")

        payload = decode_registration_ticket(ticket)
        if not payload:
            raise AuthenticationError("Registration ticket is invalid or has expired. Please verify OTP again.")

        email = payload["email"]
        account_id = int(payload["sub"])
        otp_id_str = payload.get("otp_id")
        if not otp_id_str:
            raise AuthenticationError("Registration ticket is missing verified OTP binding.")
        otp_id = UUID(otp_id_str)

        # 1. Atomically consume OTP record using conditional update
        otp_consumed = await self.otp_service.consume_otp_by_id(otp_id)
        if not otp_consumed:
            raise AuthenticationError("Registration ticket has already been used or expired.")

        # 2. Hash password with bcrypt cost factor 12
        hashed_pw = hash_password(password)

        # 3. Atomically set password only if account currently has password_hash IS NULL
        user = await self.user_repo.get_user_by_id(account_id)
        if user and user.email.lower() == email:
            success = await self.user_repo.set_initial_user_password(account_id, hashed_pw)
            actor_type = "USER"
        else:
            admin = await self.user_repo.get_admin_by_id(account_id)
            if admin and admin.email.lower() == email:
                success = await self.user_repo.set_initial_admin_password(account_id, hashed_pw)
                actor_type = "ADMIN"
            else:
                raise NotFoundError("Account not found.")

        if not success:
            raise ConflictError("Account registration has already been completed.")

        # Record audit log
        await self.audit_repo.record_event(
            action="ACCOUNT_REGISTERED",
            actor_type=actor_type,
            actor_id=account_id,
            entity_type="account",
            entity_id=str(account_id),
            details={"email": email},
        )

    # ================= Login Flow & Two-Step MFA =================
    async def login(
        self, email: str, plain_password: str
    ) -> Union[LoginResponse, LoginMFAChallengeResponse]:
        """Authenticate user or admin credentials with timing attack mitigation and optional MFA challenge."""
        clean_email = email.lower().strip()

        # Check tb_con_user first, then tb_con_admin
        user = await self.user_repo.get_user_by_email(clean_email)
        admin = None
        account_type = "USER"
        account_id: int
        role: str
        status_val: str
        stored_hash: Optional[str]

        if user:
            account_id = user.user_id
            role = user.user_type
            status_val = user.status
            stored_hash = user.password_hash
        else:
            admin = await self.user_repo.get_admin_by_email(clean_email)
            if admin:
                account_type = "ADMIN"
                account_id = admin.admin_id
                role = "ADMIN"
                status_val = admin.status
                stored_hash = admin.password_hash
            else:
                # Timing mitigation: run dummy bcrypt to ensure constant time
                verify_password(plain_password, DUMMY_HASH)
                await self.audit_repo.record_event(
                    action="LOGIN_FAILED_UNKNOWN_EMAIL",
                    actor_type="SYSTEM",
                    details={"email": clean_email},
                )
                raise AuthenticationError("Invalid email or password.")

        # Check if unregistered (password_hash IS NULL)
        if not stored_hash:
            # Timing mitigation: run dummy bcrypt
            verify_password(plain_password, DUMMY_HASH)
            await self.audit_repo.record_event(
                action="LOGIN_FAILED_UNREGISTERED_ACCOUNT",
                actor_type=account_type,
                actor_id=account_id,
                details={"email": clean_email},
            )
            raise AuthenticationError("Invalid email or password.")

        # Check account status
        if status_val == "LOCKED":
            await self.audit_repo.record_event(
                action="LOGIN_FAILED_LOCKED_ACCOUNT",
                actor_type=account_type,
                actor_id=account_id,
                details={"email": clean_email},
            )
            raise AccountStatusError("Account is locked. Please contact system administrator.")

        if status_val == "INACTIVE":
            await self.audit_repo.record_event(
                action="LOGIN_FAILED_INACTIVE_ACCOUNT",
                actor_type=account_type,
                actor_id=account_id,
                details={"email": clean_email},
            )
            raise AccountStatusError("Account is inactive.")

        # Verify password with bcrypt
        if not verify_password(plain_password, stored_hash):
            await self.audit_repo.record_event(
                action="LOGIN_FAILED_BAD_PASSWORD",
                actor_type=account_type,
                actor_id=account_id,
                details={"email": clean_email},
            )
            raise AuthenticationError("Invalid email or password.")

        # If MFA is enabled, issue challenge token and dispatch MFA OTP
        if settings.MFA_ENABLED:
            expires_sec, otp_id = await self.otp_service.initiate_mfa_otp(clean_email, account_id, account_type)
            mfa_token = create_mfa_challenge_token(
                account_id=account_id,
                email=clean_email,
                role=role,
                account_type=account_type,
                otp_id=str(otp_id),
            )
            return LoginMFAChallengeResponse(
                mfa_required=True,
                mfa_token=mfa_token,
                message="MFA verification code sent to your email.",
                expires_in_seconds=expires_sec,
            )

        # If MFA is disabled, establish session immediately
        return await self._establish_authenticated_session(account_id, clean_email, role, account_type, status_val)

    async def verify_mfa(self, mfa_token: str, code: str) -> LoginResponse:
        """Step 2 of MFA: Validate challenge token and OTP, then establish authenticated session."""
        payload = decode_mfa_challenge_token(mfa_token)
        if not payload:
            raise AuthenticationError("MFA challenge is invalid or has expired. Please log in again.")

        account_id = int(payload["sub"])
        email = payload["email"]
        role = payload["role"]
        account_type = payload["account_type"]
        otp_id = UUID(payload["otp_id"])

        # Verify and atomically consume OTP
        await self.otp_service.verify_and_consume_mfa_otp(otp_id, code, email)

        # Retrieve current status
        if account_type == "USER":
            user = await self.user_repo.get_user_by_id(account_id)
            if not user or user.status != "ACTIVE":
                raise AccountStatusError("Account is inactive or disabled.")
            status_val = user.status
        else:
            admin = await self.user_repo.get_admin_by_id(account_id)
            if not admin or admin.status != "ACTIVE":
                raise AccountStatusError("Account is inactive or disabled.")
            status_val = admin.status

        return await self._establish_authenticated_session(account_id, email, role, account_type, status_val)

    async def _establish_authenticated_session(
        self, account_id: int, email: str, role: str, account_type: str, status_val: str
    ) -> LoginResponse:
        """Create session in tb_con_user_sessions and issue token pair."""
        raw_refresh_token = create_refresh_token()
        token_hash = hash_refresh_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session_record = await self.session_repo.create_session(
            account_type=account_type,
            account_id=account_id,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
        )

        access_token = create_access_token(
            user_id=account_id,
            session_id=str(session_record.session_id),
            email=email,
            role=role,
            account_type=account_type,
        )

        await self.audit_repo.record_event(
            action="LOGIN_SUCCESS",
            actor_type=account_type,
            actor_id=account_id,
            entity_type="session",
            entity_id=str(session_record.session_id),
            details={"email": email, "role": role},
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSummary(
                user_id=account_id,
                email=email,
                role=role,
                status=status_val,
            ),
        )

    # ================= Refresh & Rotation Flow =================
    async def refresh_session(self, raw_refresh_token: str) -> TokenRefreshResponse:
        """Validate refresh token, rotate atomically, and issue new token pair."""
        token_hash = hash_refresh_token(raw_refresh_token)
        session_record = await self.session_repo.get_session_by_token_hash(token_hash)

        if not session_record:
            raise AuthenticationError("Invalid or expired refresh token.")

        if session_record.is_revoked:
            # Token reuse detection / potential token theft!
            await self.session_repo.revoke_all_account_sessions(
                session_record.account_type, session_record.account_id
            )
            await self.audit_repo.record_event(
                action="SECURITY_ALERT_REFRESH_TOKEN_REUSE",
                actor_type=session_record.account_type,
                actor_id=session_record.account_id,
                entity_type="session",
                entity_id=str(session_record.session_id),
                details={"reason": "Revoked refresh token presented. All account sessions invalidated."},
            )
            raise AuthenticationError("Session compromised. All sessions revoked. Please log in again.")

        now = datetime.now(timezone.utc)
        if now >= session_record.expires_at:
            await self.session_repo.revoke_session(session_record.session_id)
            raise AuthenticationError("Refresh token has expired. Please log in again.")

        # Conditional atomic rotation
        new_refresh_token = create_refresh_token()
        new_token_hash = hash_refresh_token(new_refresh_token)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        rotated = await self.session_repo.rotate_refresh_token(
            session_id=session_record.session_id,
            old_token_hash=token_hash,
            new_token_hash=new_token_hash,
            new_expires_at=new_expires_at,
        )
        if not rotated:
            raise AuthenticationError("Refresh token rotation conflict. Please try again.")

        # Get account details
        email: str = ""
        role: str = ""
        if session_record.account_type == "USER":
            user = await self.user_repo.get_user_by_id(session_record.account_id)
            if not user or user.status != "ACTIVE":
                raise AccountStatusError("Account is inactive or disabled.")
            email = user.email
            role = user.user_type
        else:
            admin = await self.user_repo.get_admin_by_id(session_record.account_id)
            if not admin or admin.status != "ACTIVE":
                raise AccountStatusError("Account is inactive or disabled.")
            email = admin.email
            role = "ADMIN"

        new_access_token = create_access_token(
            user_id=session_record.account_id,
            session_id=str(session_record.session_id),
            email=email,
            role=role,
            account_type=session_record.account_type,
        )

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ================= Logout Flow =================
    async def logout(
        self, session_id: UUID, account_id: int, account_type: str, all_sessions: bool = False
    ) -> None:
        """Revoke user session or all sessions."""
        if all_sessions:
            await self.session_repo.revoke_all_account_sessions(account_type, account_id)
        else:
            await self.session_repo.revoke_session(session_id)

        await self.audit_repo.record_event(
            action="LOGOUT_ALL" if all_sessions else "LOGOUT",
            actor_type=account_type,
            actor_id=account_id,
            entity_type="session",
            entity_id=str(session_id),
        )
