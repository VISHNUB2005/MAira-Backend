"""FastAPI Dependencies for Authentication, Database, and RBAC Authorization."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AccountStatusError, AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models.admin import Admin
from app.models.user import User
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.security.permissions import (
    ADMIN,
    has_permission,
    validate_role,
)

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedAccount:
    """Represents the validated authenticated actor for a request."""
    account_id: int
    session_id: UUID
    email: str
    role: str
    account_type: str  # USER, ADMIN
    status: str


async def get_current_account(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedAccount:
    """Validate Bearer JWT access token and verify database session & account status."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        account_id = int(payload["sub"])
        session_id = UUID(payload["sid"])
        account_type = payload.get("account_type", "USER").upper()
        role = payload.get("role", "STUDENT")
        email = payload.get("email", "")
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify session in tb_con_user_sessions
    session_repo = SessionRepository(session)
    session_record = await session_repo.get_session_by_id(session_id)

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session does not exist. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session_record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    if now >= session_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please refresh your token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Touch session last_used_at
    await session_repo.touch_session(session_id)

    # Verify account exists and is ACTIVE in database
    user_repo = UserRepository(session)
    status_val = "ACTIVE"

    if account_type == "USER":
        user = await user_repo.get_user_by_id(account_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")
        if user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status.lower()}. Access denied.",
            )
        status_val = user.status
        role = user.user_type
        email = user.email

    else:
        admin = await user_repo.get_admin_by_id(account_id)
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin account not found.")
        if admin.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin account is {admin.status.lower()}. Access denied.",
            )
        status_val = admin.status
        role = "ADMIN"
        email = admin.email

    return AuthenticatedAccount(
        account_id=account_id,
        session_id=session_id,
        email=email,
        role=role,
        account_type=account_type,
        status=status_val,
    )


def require_role(required_role: str):
    """Enforce specific role on an endpoint."""
    def _role_checker(account: AuthenticatedAccount = Depends(get_current_account)):
        if account.role.upper() != required_role.upper():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: requires '{required_role}' role.",
            )
        return account
    return _role_checker


def require_permission(permission: str):
    """Enforce specific permission according to RBAC matrix."""
    def _permission_checker(account: AuthenticatedAccount = Depends(get_current_account)):
        if not has_permission(account.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: missing '{permission}' permission.",
            )
        return account
    return _permission_checker


require_admin = require_role(ADMIN)
