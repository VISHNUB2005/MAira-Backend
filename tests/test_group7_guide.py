import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import logging
import smtplib
import pytest
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings


def _provider_raising(monkeypatch, exc, counter):
    class P(email_mod.EmailProvider):
        def send(self, to_email, content):
            counter["n"] += 1
            raise exc
    async def fast_sleep(_):
        pass
    monkeypatch.setattr(email_mod, "_get_provider", lambda: P())
    monkeypatch.setattr(email_mod.asyncio, "sleep", fast_sleep)


# ---------- input validation ----------
@pytest.mark.parametrize("bad", ["", "no-at-sign", "a@b", "a b@x.com", "a@x.com\r\nBcc: evil@x.com", "x" * 250 + "@a.com"])
def test_bad_email_rejected(bad):
    with pytest.raises(email_mod.EmailValidationError):
        asyncio.run(email_mod.send_login_otp(bad, "123456"))

@pytest.mark.parametrize("bad", ["", "12", "123 456", "<script>", "1" * 11])
def test_bad_otp_rejected(bad):
    with pytest.raises(email_mod.EmailValidationError):
        asyncio.run(email_mod.send_registration_otp("a@organization.com", bad))


# ---------- safe retries ----------
def test_auth_failure_is_not_retried(monkeypatch):
    calls = {"n": 0}
    _provider_raising(monkeypatch, smtplib.SMTPAuthenticationError(535, b"bad creds"), calls)
    with pytest.raises(email_mod.EmailDeliveryError):
        asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert calls["n"] == 1

def test_refused_recipient_is_not_retried(monkeypatch):
    calls = {"n": 0}
    _provider_raising(monkeypatch, smtplib.SMTPRecipientsRefused({"a@x.com": (550, b"no")}), calls)
    with pytest.raises(email_mod.EmailDeliveryError):
        asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert calls["n"] == 1

def test_timeout_is_retried_then_fails(monkeypatch):
    calls = {"n": 0}
    _provider_raising(monkeypatch, TimeoutError("timed out"), calls)
    with pytest.raises(email_mod.EmailDeliveryError):
        asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert calls["n"] == 3

def test_temporary_smtp_error_is_retried(monkeypatch):
    calls = {"n": 0}
    _provider_raising(monkeypatch, smtplib.SMTPResponseException(451, b"try later"), calls)
    with pytest.raises(email_mod.EmailDeliveryError):
        asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert calls["n"] == 3

# ---------- no OTP / secrets in logs, even on failure ----------
def test_permanent_failure_logs_have_no_otp_or_secret(monkeypatch, caplog):
    calls = {"n": 0}
    _provider_raising(monkeypatch, smtplib.SMTPAuthenticationError(535, b"password=hunter2"), calls)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(email_mod.EmailDeliveryError):
            asyncio.run(email_mod.send_login_otp("alice@organization.com", "987654"))
    assert "987654" not in caplog.text and "hunter2" not in caplog.text
    assert "alice@organization.com" not in caplog.text


# ---------- mock / test mode for Group 9 ----------
def test_mock_provider_captures_email(monkeypatch):
    monkeypatch.setattr(email_mod, "_get_provider", lambda: email_mod.MockProvider())
    email_mod.MockProvider.clear()
    r = asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert r.accepted and r.message_id == "mock-1"
    assert email_mod.MockProvider.outbox[0]["to"] == "a@organization.com"
    assert "123456" in email_mod.MockProvider.outbox[0]["text"]


# ---------- console/mock only in development/test ----------
@pytest.mark.parametrize("provider", ["console", "mock"])
@pytest.mark.parametrize("env", ["staging", "production"])
def test_dev_providers_blocked_outside_dev(monkeypatch, provider, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("EMAIL_PROVIDER", provider)
    with pytest.raises(RuntimeError, match=provider):
        Settings().validate()

@pytest.mark.parametrize("env", ["development", "test"])
def test_mock_allowed_in_dev_and_test(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    Settings().validate()
