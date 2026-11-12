"""User Profile API Endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthenticatedAccount, get_current_account, get_db
from app.schemas.user import UserProfileResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Operations"])


@router.get("/me", response_model=UserProfileResponse, summary="Get current user profile")
async def get_my_profile(
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve profile details for the authenticated student or administrator."""
    user_service = UserService(session)
    return await user_service.get_account_profile(account.account_id, account.account_type)
