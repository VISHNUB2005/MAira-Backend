"""User Session database repository."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession


class SessionRepository:
    """Repository for sch_con.tb_con_user_sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        account_type: str,
        account_id: int,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> UserSession:
        user_session = UserSession(
            account_type=account_type.upper(),
            account_id=account_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            last_used_at=datetime.now(timezone.utc),
            is_revoked=False,
        )
        self.session.add(user_session)
        await self.session.flush()
        return user_session

    async def get_session_by_id(self, session_id: UUID) -> Optional[UserSession]:
        stmt = select(UserSession).where(UserSession.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_by_token_hash(self, token_hash: str) -> Optional[UserSession]:
        stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def touch_session(self, session_id: UUID) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(last_used_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def rotate_refresh_token(
        self,
        session_id: UUID,
        old_token_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
    ) -> bool:
        """Conditional atomic rotation ensuring concurrent refresh requests cannot both succeed."""
        stmt = (
            update(UserSession)
            .where(
                UserSession.session_id == session_id,
                UserSession.refresh_token_hash == old_token_hash,
                UserSession.is_revoked.is_(False),
            )
            .values(
                refresh_token_hash=new_token_hash,
                expires_at=new_expires_at,
                last_used_at=func.now(),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def revoke_session(self, session_id: UUID) -> bool:
        stmt = (
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(is_revoked=True, revoked_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def revoke_all_account_sessions(self, account_type: str, account_id: int) -> int:
        stmt = (
            update(UserSession)
            .where(
                UserSession.account_type == account_type.upper(),
                UserSession.account_id == account_id,
                UserSession.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
