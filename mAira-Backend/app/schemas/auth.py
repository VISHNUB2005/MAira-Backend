"""Authentication request and response schemas."""

from typing import Optional, Union
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterInitiateRequest(BaseModel):
    email: EmailStr


class RegisterInitiateResponse(BaseModel):
    message: str
    email: str
    expires_in_seconds: int


class RegisterVerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=6)

    @field_validator("otp")
    @classmethod
    def validate_otp_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only numeric digits.")
        return v


class RegisterVerifyOtpResponse(BaseModel):
    message: str
    registration_ticket: str
    expires_in_minutes: int


class RegisterCompletePasswordRequest(BaseModel):
    registration_ticket: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        # Check for special character
        special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
        has_special = any(c in special_chars for c in v)
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must include at least one uppercase letter, one lowercase letter, "
                "one number, and one special character."
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserSummary(BaseModel):
    user_id: int
    email: str
    role: str
    status: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class LoginMFAChallengeResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str
    message: str = "MFA verification code sent to your email."
    expires_in_seconds: int = 300


class MFAVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("MFA code must be 6 numeric digits.")
        return v


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    all_sessions: bool = False
