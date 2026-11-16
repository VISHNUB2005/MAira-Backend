"""SQLAlchemy Model for sch_con.tb_con_messages."""

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class Message(Base):
    """Chat message model."""

    __tablename__ = "tb_con_messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_session_id = Column(UUID(as_uuid=True), ForeignKey("sch_con.tb_con_chat_sessions.chat_session_id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # USER, ASSISTANT
    content = Column(Text, nullable=False)
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("sch_con.tb_con_messages.message_id"), nullable=True)
    status = Column(String(20), nullable=False, default="COMPLETED")  # PENDING, COMPLETED, FAILED
    model_name = Column(String(120), nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    chat_session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.message_id} sender={self.sender} status={self.status}>"
