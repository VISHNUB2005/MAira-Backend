"""FastAPI routes for secure password setup."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from modules.m_auth.m_auth_password_setup import (
    InvalidRegistrationToken,
    PasswordSetupNotAllowed,
    PasswordSetupService,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Password Security"])


class PasswordSetupRequest(BaseModel):
    registration_token: str = Field(min_length=1, max_length=4096)
    password: str = Field(min_length=1, max_length=1024)


class PasswordSetupResponse(BaseModel):
    message: str


def get_password_setup_service(request: Request) -> PasswordSetupService:
    service = getattr(request.app.state, "password_setup_service", None)

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password setup service is not configured.",
        )

    return service


@router.post(
    "/password/setup",
    response_model=PasswordSetupResponse,
    status_code=status.HTTP_200_OK,
)
def setup_password(
    payload: PasswordSetupRequest,
    service: Annotated[
        PasswordSetupService, Depends(get_password_setup_service)
    ],
):
    try:
        service.setup_password(
            token=payload.registration_token,
            password=payload.password,
        )
    except InvalidRegistrationToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration token.",
        )
    except PasswordSetupNotAllowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password setup is not allowed for this account.",
        )

    return PasswordSetupResponse(
        message="Password setup completed successfully."
    )
