"""SQLAlchemy Model for sch_con.tb_con_otp_verification."""

import uuid
from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class OTPVerification(Base):
    """OTP verification records for registration and MFA."""

    __tablename__ = "tb_con_otp_verification"

    otp_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String(20), nullable=True)  # USER, ADMIN
    account_id = Column(BigInteger, nullable=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(String(30), nullable=False)  # REGISTRATION, LOGIN_MFA, PASSWORD_RESET
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(SmallInteger, nullable=False, default=0)
    max_attempts = Column(SmallInteger, nullable=False, default=5)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<OTPVerification id={self.otp_id} email={self.email} purpose={self.purpose} attempts={self.attempts}>"
