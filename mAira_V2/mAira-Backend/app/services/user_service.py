"""User and Admin Management Service."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.audit_repo import AuditRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import (
    StudentAnalyticsResponse,
    StudentItem,
    StudentListResponse,
)
from app.schemas.user import UserProfileResponse


class UserService:
    """Handles user profile and administrator operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.audit_repo = AuditRepository(session)

    # ================= Profile =================
    async def get_account_profile(
        self, account_id: int, account_type: str = "USER"
    ) -> UserProfileResponse:
        """Retrieve profile details for either student or administrator."""
        if account_type.upper() == "ADMIN":
            admin = await self.user_repo.get_admin_by_id(account_id)
            if not admin:
                raise NotFoundError("Administrator account not found.")
            return UserProfileResponse(
                user_id=admin.admin_id,
                email=admin.email,
                user_type="ADMIN",
                status=admin.status,
                created_at=admin.created_at,
                updated_at=admin.updated_at,
            )

        user = await self.user_repo.get_user_by_id(account_id)
        if not user:
            raise NotFoundError("User not found.")
        return UserProfileResponse(
            user_id=user.user_id,
            email=user.email,
            user_type=user.user_type,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    # ================= Admin Operations =================
    async def admin_create_student(
        self, admin_id: int, email: str, name: Optional[str] = None, user_type: str = "STUDENT"
    ) -> StudentItem:
        clean_email = email.lower().strip()
        existing = await self.user_repo.get_user_by_email(clean_email)
        if existing:
            raise ConflictError("User account with this email already exists.")

        user = await self.user_repo.create_user(
            email=clean_email, user_type=user_type, status="ACTIVE"
        )

        await self.audit_repo.record_event(
            action="ADMIN_CREATE_STUDENT",
            actor_type="ADMIN",
            actor_id=admin_id,
            entity_type="user",
            entity_id=str(user.user_id),
            details={"email": clean_email, "user_type": user_type},
        )

        return StudentItem(
            user_id=user.user_id,
            email=user.email,
            user_type=user.user_type,
            status=user.status,
            password_set=user.password_hash is not None,
            created_at=user.created_at,
        )

    async def admin_list_students(
        self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
    ) -> StudentListResponse:
        total = await self.user_repo.count_users(status_filter=status_filter)
        users = await self.user_repo.list_users(limit=limit, offset=offset, status_filter=status_filter)
        items = [
            StudentItem(
                user_id=u.user_id,
                email=u.email,
                user_type=u.user_type,
                status=u.status,
                password_set=u.password_hash is not None,
                created_at=u.created_at,
            )
            for u in users
        ]
        return StudentListResponse(total=total, students=items)

    async def admin_get_student(self, user_id: int) -> StudentItem:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("Student account not found.")
        return StudentItem(
            user_id=user.user_id,
            email=user.email,
            user_type=user.user_type,
            status=user.status,
            password_set=user.password_hash is not None,
            created_at=user.created_at,
        )

    async def admin_update_student_status(
        self, admin_id: int, user_id: int, new_status: str
    ) -> StudentItem:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("Student account not found.")

        old_status = user.status
        await self.user_repo.update_user_status(user_id, new_status)

        # Deactivation immediately revokes that student's active sessions
        if new_status.upper() != "ACTIVE":
            revoked_count = await self.session_repo.revoke_all_account_sessions("USER", user_id)
        else:
            revoked_count = 0

        await self.audit_repo.record_event(
            action="ADMIN_UPDATE_USER_STATUS",
            actor_type="ADMIN",
            actor_id=admin_id,
            entity_type="user",
            entity_id=str(user_id),
            details={
                "old_status": old_status,
                "new_status": new_status,
                "revoked_sessions": revoked_count,
            },
        )

        return StudentItem(
            user_id=user.user_id,
            email=user.email,
            user_type=user.user_type,
            status=new_status.upper(),
            password_set=user.password_hash is not None,
            created_at=user.created_at,
        )

    async def admin_delete_student(self, admin_id: int, user_id: int) -> bool:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("Student account not found.")

        email = user.email
        await self.session_repo.revoke_all_account_sessions("USER", user_id)
        success = await self.user_repo.delete_user(user_id)

        await self.audit_repo.record_event(
            action="ADMIN_DELETE_USER",
            actor_type="ADMIN",
            actor_id=admin_id,
            entity_type="user",
            entity_id=str(user_id),
            details={"email": email},
        )
        return success

    async def admin_get_analytics(self) -> StudentAnalyticsResponse:
        total, active, inactive = await self.user_repo.get_user_analytics_summary()
        return StudentAnalyticsResponse(
            total_students=total,
            active_students=active,
            inactive_students=inactive,
        )
