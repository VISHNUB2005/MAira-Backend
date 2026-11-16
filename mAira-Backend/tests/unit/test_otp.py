"""Unit tests for OTP generation and hashing."""

import pytest
from app.core.security import generate_secure_otp, hash_otp, verify_otp_hash


def test_otp_generation():
    otp = generate_secure_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()

    otp4 = generate_secure_otp(4)
    assert len(otp4) == 4
    assert otp4.isdigit()


def test_otp_hashing_and_verification():
    email = "applicant@example.com"
    otp = "654321"
    h = hash_otp(otp, email)

    assert len(h) == 64
    assert verify_otp_hash(otp, h, email) is True
    assert verify_otp_hash("000000", h, email) is False
    assert verify_otp_hash(otp, h, "wrong@example.com") is False
    assert verify_otp_hash("", h, email) is False
