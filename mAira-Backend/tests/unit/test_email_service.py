"""Unit tests for EmailService, SMTP dispatch, timeout handling, and leak prevention."""

from unittest.mock import MagicMock, patch
import pytest
import smtplib

from app.services.email_service import EmailContent, EmailService, MockEmailProvider


@pytest.fixture(autouse=True)
def clean_mock_outbox():
    MockEmailProvider.clear()
    yield
    MockEmailProvider.clear()


@pytest.mark.asyncio
async def test_send_registration_otp_mock_provider():
    service = EmailService()
    service.provider = "mock"

    res = await service.send_registration_otp("student@institution.edu", "123456")
    assert res.accepted is True
    assert res.provider == "mock"

    latest = MockEmailProvider.get_latest_for("student@institution.edu")
    assert latest is not None
    assert "Registration Verification Code" in latest["subject"]
    assert "123456" in latest["text"]


@pytest.mark.asyncio
async def test_send_login_mfa_otp_mock_provider():
    service = EmailService()
    service.provider = "mock"

    res = await service.send_login_mfa_otp("student@institution.edu", "654321")
    assert res.accepted is True
    assert res.provider == "mock"

    latest = MockEmailProvider.get_latest_for("student@institution.edu")
    assert latest is not None
    assert "Login Verification Code" in latest["subject"]
    assert "654321" in latest["text"]


@pytest.mark.asyncio
async def test_smtp_send_success():
    service = EmailService()
    service.provider = "smtp"

    mock_server = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_server):
        mock_server.__enter__.return_value = mock_server

        res = await service.send_email(
            "student@institution.edu",
            EmailContent(subject="Test Subject", text_body="Hello Student"),
        )
        assert res.accepted is True
        assert res.provider == "smtp"
        assert mock_server.send_message.called


@pytest.mark.asyncio
async def test_smtp_authentication_failure_sanitized():
    service = EmailService()
    service.provider = "smtp"

    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication credentials invalid")

    with patch("smtplib.SMTP", return_value=mock_server):
        mock_server.__enter__.return_value = mock_server

        res = await service.send_email(
            "student@institution.edu",
            EmailContent(subject="Alert", text_body="Security notice"),
        )
        assert res.accepted is False
        # Verify sanitized error message without credential leakage
        assert res.error == "SMTP authentication failure"


@pytest.mark.asyncio
async def test_smtp_timeout_handling():
    service = EmailService()
    service.provider = "smtp"

    with patch("smtplib.SMTP", side_effect=TimeoutError("Connection timed out")):
        res = await service.send_email(
            "student@institution.edu",
            EmailContent(subject="Alert", text_body="Security notice"),
        )
        assert res.accepted is False
        assert res.error == "SMTP connection timeout or unreachable"
