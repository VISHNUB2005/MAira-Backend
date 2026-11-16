"""SQLAlchemy Model for sch_con.tb_con_user_sessions."""

import uuid
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class UserSession(Base):
    """User authentication session model storing refresh-token hash."""

    __tablename__ = "tb_con_user_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String(20), nullable=False)  # USER, ADMIN
    account_id = Column(BigInteger, nullable=False, index=True)
    refresh_token_hash = Column(Text, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<UserSession id={self.session_id} account_type={self.account_type} account_id={self.account_id} is_revoked={self.is_revoked}>"
