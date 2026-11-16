"""Admin Management Endpoints (matching RBAC specifications and canonical routes)."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AuthenticatedAccount,
    get_current_account,
    get_db,
    require_permission,
)
from app.schemas.admin import (
    StudentAnalyticsResponse,
    StudentCreate,
    StudentItem,
    StudentListResponse,
    StudentStatusUpdate,
)
from app.schemas.common import MessageOnlyResponse
from app.security.permissions import (
    STUDENT_ACTIVATE,
    STUDENT_ANALYTICS_VIEW,
    STUDENT_CREATE,
    STUDENT_DEACTIVATE,
    STUDENT_DELETE,
    STUDENT_VIEW_BASIC,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


@router.post(
    "/students",
    response_model=StudentItem,
    status_code=status.HTTP_201_CREATED,
    summary="Pre-approve institutional student account",
)
@router.post(
    "/",
    response_model=StudentItem,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    summary="Legacy root alias for creating student",
)
async def create_student(
    payload: StudentCreate,
    admin: AuthenticatedAccount = Depends(require_permission(STUDENT_CREATE)),
    session: AsyncSession = Depends(get_db),
):
    """Add a student email to the database allowlist for registration."""
    user_service = UserService(session)
    return await user_service.admin_create_student(
        admin_id=admin.account_id,
        email=str(payload.email),
        name=payload.name,
        user_type=payload.user_type,
    )


@router.get(
    "/students",
    response_model=StudentListResponse,
    summary="List all student accounts",
)
@router.get(
    "/",
    response_model=StudentListResponse,
    include_in_schema=False,
    summary="Legacy root alias for listing students",
)
async def list_students(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    admin: AuthenticatedAccount = Depends(require_permission(STUDENT_VIEW_BASIC)),
    session: AsyncSession = Depends(get_db),
):
    """View basic student account details."""
    user_service = UserService(session)
    return await user_service.admin_list_students(
        limit=limit, offset=offset, status_filter=status
    )


@router.get(
    "/analytics",
    response_model=StudentAnalyticsResponse,
    summary="Get student account analytics",
)
@router.get(
    "/analytics/summary",
    response_model=StudentAnalyticsResponse,
    include_in_schema=False,
    summary="Legacy alias for analytics",
)
async def get_analytics_summary(
    admin: AuthenticatedAccount = Depends(require_permission(STUDENT_ANALYTICS_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    """Return aggregated account metrics: total, active, and inactive."""
    user_service = UserService(session)
    return await user_service.admin_get_analytics()


@router.get(
    "/students/{user_id}",
    response_model=StudentItem,
    summary="Get single student details",
)
@router.get(
    "/{user_id}",
    response_model=StudentItem,
    include_in_schema=False,
    summary="Legacy alias for single student details",
)
async def get_student(
    user_id: int,
    admin: AuthenticatedAccount = Depends(require_permission(STUDENT_VIEW_BASIC)),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve basic details of a single student account."""
    user_service = UserService(session)
    return await user_service.admin_get_student(user_id)


@router.patch(
    "/students/{user_id}/status",
    response_model=StudentItem,
    summary="Update student account status (ACTIVE/INACTIVE)",
)
@router.patch(
    "/{user_id}/status",
    response_model=StudentItem,
    include_in_schema=False,
    summary="Legacy alias for status update",
)
async def update_student_status(
    user_id: int,
    payload: StudentStatusUpdate,
    admin: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a student account; deactivation immediately revokes active sessions."""
    perm = STUDENT_ACTIVATE if payload.status == "ACTIVE" else STUDENT_DEACTIVATE
    require_permission(perm)(admin)

    user_service = UserService(session)
    return await user_service.admin_update_student_status(
        admin_id=admin.account_id,
        user_id=user_id,
        new_status=payload.status,
    )


@router.delete(
    "/students/{user_id}",
    response_model=MessageOnlyResponse,
    summary="Delete a student account",
)
@router.delete(
    "/{user_id}",
    response_model=MessageOnlyResponse,
    include_in_schema=False,
    summary="Legacy alias for student delete",
)
async def delete_student(
    user_id: int,
    admin: AuthenticatedAccount = Depends(require_permission(STUDENT_DELETE)),
    session: AsyncSession = Depends(get_db),
):
    """Delete a student account."""
    user_service = UserService(session)
    await user_service.admin_delete_student(admin_id=admin.account_id, user_id=user_id)
    return MessageOnlyResponse(message=f"Student account {user_id} deleted successfully.")
