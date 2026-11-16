"""User and Admin database repository."""

from typing import List, Optional, Tuple
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User


class UserRepository:
    """Repository for sch_con.tb_con_user and sch_con.tb_con_admin."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ================= User Operations =================
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
    ) -> List[User]:
        stmt = select(User)
        if status_filter:
            stmt = stmt.where(User.status == status_filter.upper())
        stmt = stmt.order_by(User.user_id.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_users(self, status_filter: Optional[str] = None) -> int:
        stmt = select(func.count(User.user_id))
        if status_filter:
            stmt = stmt.where(User.status == status_filter.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_user_analytics_summary(self) -> Tuple[int, int, int]:
        """Returns (total_users, active_users, inactive_users)."""
        total = await self.count_users()
        active = await self.count_users(status_filter="ACTIVE")
        inactive = await self.count_users(status_filter="INACTIVE")
        return total, active, inactive

    async def create_user(
        self, email: str, user_type: str = "STUDENT", status: str = "ACTIVE"
    ) -> User:
        user = User(
            email=email.lower().strip(),
            user_type=user_type.upper(),
            password_hash=None,
            status=status.upper(),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_initial_user_password(self, user_id: int, password_hash: str) -> bool:
        """Atomically set password only if currently unregistered (password_hash IS NULL)."""
        stmt = (
            update(User)
            .where(User.user_id == user_id, User.password_hash.is_(None))
            .values(password_hash=password_hash, updated_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_user_password(self, user_id: int, password_hash: str) -> Optional[User]:
        user = await self.get_user_by_id(user_id)
        if user:
            user.password_hash = password_hash
            await self.session.flush()
        return user

    async def update_user_status(self, user_id: int, status: str) -> Optional[User]:
        user = await self.get_user_by_id(user_id)
        if user:
            user.status = status.upper()
            await self.session.flush()
        return user

    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.flush()
            return True
        return False

    # ================= Admin Operations =================
    async def get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        stmt = select(Admin).where(Admin.admin_id == admin_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admin_by_email(self, email: str) -> Optional[Admin]:
        stmt = select(Admin).where(func.lower(Admin.email) == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_initial_admin_password(self, admin_id: int, password_hash: str) -> bool:
        """Atomically set admin password only if currently unregistered (password_hash IS NULL)."""
        stmt = (
            update(Admin)
            .where(Admin.admin_id == admin_id, Admin.password_hash.is_(None))
            .values(password_hash=password_hash, updated_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_admin_password(self, admin_id: int, password_hash: str) -> Optional[Admin]:
        admin = await self.get_admin_by_id(admin_id)
        if admin:
            admin.password_hash = password_hash
            await self.session.flush()
        return admin
