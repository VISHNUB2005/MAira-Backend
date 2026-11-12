"""OTP Verification database repository."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTPVerification


class OTPRepository:
    """Repository for sch_con.tb_con_otp_verification."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_otp(
        self,
        email: str,
        otp_hash: str,
        purpose: str,
        expires_at: datetime,
        max_attempts: int = 5,
        account_type: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> OTPVerification:
        otp = OTPVerification(
            email=email.lower().strip(),
            otp_hash=otp_hash,
            purpose=purpose.upper(),
            expires_at=expires_at,
            max_attempts=max_attempts,
            attempts=0,
            account_type=account_type.upper() if account_type else None,
            account_id=account_id,
        )
        self.session.add(otp)
        await self.session.flush()
        return otp

    async def get_otp_by_id(self, otp_id: UUID) -> Optional[OTPVerification]:
        """Fetch OTP verification record by its primary key."""
        stmt = select(OTPVerification).where(OTPVerification.otp_id == otp_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_active_otp(
        self, email: str, purpose: str
    ) -> Optional[OTPVerification]:
        """Fetch the most recent unused OTP for given email and purpose."""
        stmt = (
            select(OTPVerification)
            .where(
                func.lower(OTPVerification.email) == email.lower().strip(),
                OTPVerification.purpose == purpose.upper(),
                OTPVerification.used_at.is_(None),
            )
            .order_by(OTPVerification.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_attempts(self, otp_id: UUID) -> int:
        stmt = (
            update(OTPVerification)
            .where(OTPVerification.otp_id == otp_id)
            .values(attempts=OTPVerification.attempts + 1)
            .returning(OTPVerification.attempts)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def mark_verified(self, otp_id: UUID) -> bool:
        stmt = (
            update(OTPVerification)
            .where(OTPVerification.otp_id == otp_id)
            .values(verified_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def mark_used(self, otp_id: UUID) -> bool:
        """Atomically mark verified OTP as consumed.
        
        Requires verified_at IS NOT NULL and used_at IS NULL to prevent replay.
        """
        stmt = (
            update(OTPVerification)
            .where(
                OTPVerification.otp_id == otp_id,
                OTPVerification.verified_at.is_not(None),
                OTPVerification.used_at.is_(None),
            )
            .values(used_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
