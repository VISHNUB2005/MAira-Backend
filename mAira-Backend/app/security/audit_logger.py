"""Centralized Audit Logging Service."""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import AuditRepository

logger = logging.getLogger("maira.audit")


class AuditLogger:
    """Helper to record standardized security events."""

    @staticmethod
    async def log_event(
        session: AsyncSession,
        action: str,
        actor_type: Optional[str] = None,
        actor_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            repo = AuditRepository(session)
            await repo.record_event(
                action=action,
                actor_type=actor_type,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
        except Exception as e:
            logger.error(f"Failed to record audit event '{action}': {e}", exc_info=True)
