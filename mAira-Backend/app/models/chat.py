"""SQLAlchemy Model for sch_con.tb_con_chat_sessions."""

import uuid
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class ChatSession(Base):
    """Chat session / conversation history metadata."""

    __tablename__ = "tb_con_chat_sessions"

    chat_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String(20), nullable=False)  # USER, ADMIN
    account_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="chat_session", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self) -> str:
        return f"<ChatSession id={self.chat_session_id} account_id={self.account_id} title='{self.title}'>"
