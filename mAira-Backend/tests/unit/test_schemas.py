"""Unit tests for Pydantic input validation schemas."""

import pytest
from pydantic import ValidationError
from app.schemas.auth import (
    LoginRequest,
    RegisterCompletePasswordRequest,
    RegisterInitiateRequest,
    RegisterVerifyOtpRequest,
)


def test_register_initiate_schema():
    req = RegisterInitiateRequest(email="valid.student@institution.edu")
    assert req.email == "valid.student@institution.edu"

    with pytest.raises(ValidationError):
        RegisterInitiateRequest(email="not-an-email")


def test_otp_verification_schema():
    req = RegisterVerifyOtpRequest(email="student@example.com", otp="123456")
    assert req.otp == "123456"

    # Non-digits rejected
    with pytest.raises(ValidationError):
        RegisterVerifyOtpRequest(email="student@example.com", otp="12ab56")

    # Wrong length
    with pytest.raises(ValidationError):
        RegisterVerifyOtpRequest(email="student@example.com", otp="12")


def test_password_complexity_schema():
    # Valid password
    req = RegisterCompletePasswordRequest(
        registration_ticket="valid_ticket",
        password="ValidPassword123!",
        confirm_password="ValidPassword123!",
    )
    assert req.password == "ValidPassword123!"

    # Too short
    with pytest.raises(ValidationError):
        RegisterCompletePasswordRequest(
            registration_ticket="ticket",
            password="Short1!",
            confirm_password="Short1!",
        )

    # Missing number
    with pytest.raises(ValidationError):
        RegisterCompletePasswordRequest(
            registration_ticket="ticket",
            password="NoNumberPassword!",
            confirm_password="NoNumberPassword!",
        )

    # Missing uppercase
    with pytest.raises(ValidationError):
        RegisterCompletePasswordRequest(
            registration_ticket="ticket",
            password="lowercasepassword123!",
            confirm_password="lowercasepassword123!",
        )
