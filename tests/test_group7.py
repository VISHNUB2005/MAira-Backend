import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import pytest
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings
from xsc_lib.xsc_lib_app.xsc_lib_a_secrets import get_secret, mask_secret, MissingSecretError

def test_get_secret_from_env(monkeypatch):
    monkeypatch.setenv("MY_TEST_SECRET", "abc")
    assert get_secret("MY_TEST_SECRET") == "abc"

def test_required_secret_missing_raises(monkeypatch):
    monkeypatch.delenv("NOPE_SECRET", raising=False)
    with pytest.raises(MissingSecretError):
        get_secret("NOPE_SECRET", required=True)

def test_mask_secret():
    assert mask_secret("abcdefghij") == "ab********ij"
    assert mask_secret(None) == "<empty>"

def test_short_jwt_key_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings().validate()

def test_console_email_blocked_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    with pytest.raises(RuntimeError, match="console"):
        Settings().validate()

def test_otp_appears_in_both_bodies():
    c = email_mod.build_registration_email("123456")
    assert "123456" in c.text_body and "123456" in c.html_body

def test_html_is_escaped():
    c = email_mod.build_login_email("<b>1</b>")
    assert "<b>1</b>" not in c.html_body

def _patch_provider(monkeypatch, fail_times):
    calls = {"n": 0}
    class Flaky(email_mod.EmailProvider):
        def send(self, to_email, content):
            calls["n"] += 1
            if calls["n"] <= fail_times:
                raise ConnectionError("boom")
    async def fast_sleep(_):
        pass
    monkeypatch.setattr(email_mod, "_get_provider", lambda: Flaky())
    monkeypatch.setattr(email_mod.asyncio, "sleep", fast_sleep)
    return calls

def test_retries_then_succeeds(monkeypatch):
    calls = _patch_provider(monkeypatch, fail_times=2)
    assert asyncio.run(email_mod.send_login_otp("a@organization.com", "111111")).accepted is True
    assert calls["n"] == 3

def test_raises_after_all_retries_fail(monkeypatch):
    _patch_provider(monkeypatch, fail_times=99)
    with pytest.raises(email_mod.EmailDeliveryError):
        asyncio.run(email_mod.send_registration_otp("a@organization.com", "111111"))
