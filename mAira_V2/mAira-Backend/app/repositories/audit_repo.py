"""Audit Log database repository."""

from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.utils.redaction import redact_sensitive_dict


class AuditRepository:
    """Repository for sch_con.tb_con_audit_log."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_event(
        self,
        action: str,
        actor_type: Optional[str] = None,
        actor_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        # Guarantee sensitive values are never persisted into audit details
        sanitized_details = redact_sensitive_dict(details or {})

        log_entry = AuditLog(
            action=action.upper(),
            actor_type=actor_type.upper() if actor_type else None,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=sanitized_details,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
