
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.m_auth.m_auth_sm_session import (
    get_jwt_secret_key,
    verify_access_token,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate JWT configuration when the application starts.
    app.state.jwt_secret_key = get_jwt_secret_key()
    yield


app = FastAPI(
    title="MAira Backend",
    description="MAira backend API",
    version="1.0.0",
    lifespan=lifespan,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    """Validate the access token and return its claims."""

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials are missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(
        credentials.credentials,
        request.app.state.jwt_secret_key,
    )

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def require_roles(*allowed_roles: str):
    """Restrict access to users with approved roles."""

    allowed = {role.upper() for role in allowed_roles}

    def role_checker(
        current_user: dict = Depends(get_current_user),
    ):
        user_role = (current_user.get("role") or "").upper()

        if user_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_checker


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MAira Backend",
    }


@app.get("/api/v1/protected/test")
def protected_test(
    current_user: dict = Depends(get_current_user),
):
    return {
        "message": "Authentication successful",
        "user_id": current_user["sub"],
        "session_id": current_user["sid"],
        "role": current_user.get("role"),
    }


@app.get("/api/v1/user/dashboard")
def user_dashboard(
    current_user: dict = Depends(require_roles("USER")),
):
    return {
        "message": "USER dashboard access granted",
        "user_id": current_user["sub"],
        "role": current_user["role"],
    }


@app.get("/api/v1/admin/dashboard")
def admin_dashboard(
    current_user: dict = Depends(require_roles("ADMIN")),
):
    return {
        "message": "ADMIN dashboard access granted",
        "user_id": current_user["sub"],
        "role": current_user["role"],
    }
