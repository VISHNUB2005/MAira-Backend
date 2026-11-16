"""SQLAlchemy Model for sch_con.tb_con_audit_log."""

from sqlalchemy import BigInteger, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base


class AuditLog(Base):
    """Audit log records for security and compliance tracking."""

    __tablename__ = "tb_con_audit_log"

    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_type = Column(String(20), nullable=True)  # USER, ADMIN, SYSTEM
    actor_id = Column(BigInteger, nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(String(100), nullable=True)
    event_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    details = Column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.audit_id} action='{self.action}' actor='{self.actor_type}:{self.actor_id}'>"
