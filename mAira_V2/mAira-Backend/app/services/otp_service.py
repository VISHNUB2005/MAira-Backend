"""OTP Service for Registration and Login MFA."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import OTPError
from app.core.security import generate_secure_otp, hash_otp, verify_otp_hash
from app.models.otp import OTPVerification
from app.repositories.audit_repo import AuditRepository
from app.repositories.otp_repo import OTPRepository
from app.services.email_service import EmailService

settings = get_settings()


class OTPService:
    """Manages the OTP lifecycle, hashing, attempt limiting, expiration, and atomic single-use consumption."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.otp_repo = OTPRepository(session)
        self.audit_repo = AuditRepository(session)
        self.email_service = EmailService()

    # ================= Registration OTP Lifecycle =================
    async def initiate_registration_otp(
        self, email: str, account_id: Optional[int] = None
    ) -> Tuple[int, UUID]:
        """Generate, persist hash, and dispatch registration OTP. Returns (expiry_seconds, otp_id)."""
        code = generate_secure_otp(6)
        otp_hash = hash_otp(code, email)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        otp_record = await self.otp_repo.create_otp(
            email=email,
            otp_hash=otp_hash,
            purpose="REGISTRATION",
            expires_at=expires_at,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            account_type="USER",
            account_id=account_id,
        )

        # Dispatch transactional email
        send_result = await self.email_service.send_registration_otp(email, code)
        if not send_result.accepted:
            raise OTPError(f"Failed to dispatch verification email: {send_result.error or 'Email service error'}")

        await self.audit_repo.record_event(
            action="REGISTRATION_OTP_SENT",
            actor_type="USER",
            actor_id=account_id,
            entity_type="otp_verification",
            entity_id=str(otp_record.otp_id),
            details={"email": email, "purpose": "REGISTRATION"},
        )

        return settings.OTP_EXPIRY_MINUTES * 60, otp_record.otp_id

    async def verify_registration_otp(self, email: str, code: str) -> UUID:
        """Verify OTP for registration, enforcing expiration and attempt limits.

        Returns the verified otp_id for binding to the registration ticket.
        """
        otp_record = await self.otp_repo.get_latest_active_otp(email, purpose="REGISTRATION")
        if not otp_record:
            raise OTPError("No active verification code found for this email.")

        now = datetime.now(timezone.utc)
        if now > otp_record.expires_at:
            await self.audit_repo.record_event(
                action="OTP_VERIFICATION_EXPIRED",
                actor_type="USER",
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
                details={"email": email, "purpose": "REGISTRATION"},
            )
            raise OTPError("Verification code has expired. Please request a new one.")

        if otp_record.attempts >= otp_record.max_attempts:
            await self.audit_repo.record_event(
                action="OTP_MAX_ATTEMPTS_EXCEEDED",
                actor_type="USER",
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
                details={"email": email, "purpose": "REGISTRATION", "attempts": otp_record.attempts},
            )
            raise OTPError("Maximum verification attempts exceeded. Please request a new code.")

        # Constant-time comparison
        is_valid = verify_otp_hash(code, otp_record.otp_hash, email)

        if not is_valid:
            new_attempts = await self.otp_repo.increment_attempts(otp_record.otp_id)
            await self.audit_repo.record_event(
                action="OTP_VERIFICATION_FAILED",
                actor_type="USER",
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
                details={"email": email, "purpose": "REGISTRATION", "attempt": new_attempts},
            )
            remaining = otp_record.max_attempts - new_attempts
            raise OTPError(f"Invalid verification code. {max(0, remaining)} attempt(s) remaining.")

        # Mark verified atomically
        await self.otp_repo.mark_verified(otp_record.otp_id)
        await self.audit_repo.record_event(
            action="REGISTRATION_OTP_VERIFIED",
            actor_type="USER",
            actor_id=otp_record.account_id,
            entity_type="otp_verification",
            entity_id=str(otp_record.otp_id),
            details={"email": email, "purpose": "REGISTRATION"},
        )
        return otp_record.otp_id

    async def consume_otp_by_id(self, otp_id: UUID) -> bool:
        """Atomically mark verified OTP as consumed so it cannot be replayed."""
        return await self.otp_repo.mark_used(otp_id)

    # ================= Login MFA OTP Lifecycle =================
    async def initiate_mfa_otp(
        self, email: str, account_id: int, account_type: str = "USER"
    ) -> Tuple[int, UUID]:
        """Generate, persist hash, and dispatch MFA verification OTP. Returns (expiry_seconds, otp_id)."""
        code = generate_secure_otp(6)
        otp_hash = hash_otp(code, email)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.MFA_EXPIRY_MINUTES)

        otp_record = await self.otp_repo.create_otp(
            email=email,
            otp_hash=otp_hash,
            purpose="LOGIN_MFA",
            expires_at=expires_at,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            account_type=account_type,
            account_id=account_id,
        )

        send_result = await self.email_service.send_login_mfa_otp(email, code)
        if not send_result.accepted:
            raise OTPError(f"Failed to dispatch MFA email: {send_result.error or 'Email service error'}")

        await self.audit_repo.record_event(
            action="LOGIN_MFA_OTP_SENT",
            actor_type=account_type,
            actor_id=account_id,
            entity_type="otp_verification",
            entity_id=str(otp_record.otp_id),
            details={"email": email, "purpose": "LOGIN_MFA"},
        )

        return settings.MFA_EXPIRY_MINUTES * 60, otp_record.otp_id

    async def verify_and_consume_mfa_otp(self, otp_id: UUID, code: str, email: str) -> bool:
        """Verify and atomically consume the MFA OTP in one step."""
        otp_record = await self.otp_repo.get_otp_by_id(otp_id)
        if not otp_record or otp_record.purpose != "LOGIN_MFA":
            raise OTPError("Invalid MFA challenge.")

        if otp_record.used_at is not None:
            raise OTPError("MFA challenge has already been consumed. Please log in again.")

        if otp_record.email.lower() != email.lower().strip():
            raise OTPError("MFA email binding mismatch.")

        now = datetime.now(timezone.utc)
        if now > otp_record.expires_at:
            await self.audit_repo.record_event(
                action="MFA_OTP_EXPIRED",
                actor_type=otp_record.account_type,
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
            )
            raise OTPError("MFA verification code has expired. Please log in again.")

        if otp_record.attempts >= otp_record.max_attempts:
            await self.audit_repo.record_event(
                action="MFA_OTP_MAX_ATTEMPTS_EXCEEDED",
                actor_type=otp_record.account_type,
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
            )
            raise OTPError("Maximum MFA verification attempts exceeded. Please log in again.")

        is_valid = verify_otp_hash(code, otp_record.otp_hash, email)
        if not is_valid:
            new_attempts = await self.otp_repo.increment_attempts(otp_record.otp_id)
            await self.audit_repo.record_event(
                action="MFA_OTP_FAILED",
                actor_type=otp_record.account_type,
                actor_id=otp_record.account_id,
                entity_type="otp_verification",
                entity_id=str(otp_record.otp_id),
                details={"attempt": new_attempts},
            )
            remaining = otp_record.max_attempts - new_attempts
            raise OTPError(f"Invalid MFA code. {max(0, remaining)} attempt(s) remaining.")

        # Mark verified and used atomically
        await self.otp_repo.mark_verified(otp_record.otp_id)
        consumed = await self.otp_repo.mark_used(otp_record.otp_id)
        if not consumed:
            raise OTPError("MFA challenge was already used. Please log in again.")

        await self.audit_repo.record_event(
            action="MFA_OTP_VERIFIED",
            actor_type=otp_record.account_type,
            actor_id=otp_record.account_id,
            entity_type="otp_verification",
            entity_id=str(otp_record.otp_id),
        )
        return True
