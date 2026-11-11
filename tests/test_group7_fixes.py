import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings


# ---- Fix 1: accepted vs confirmed ----
def _ok_provider(monkeypatch, message_id):
    class Ok(email_mod.EmailProvider):
        def send(self, to_email, content):
            return message_id
    monkeypatch.setattr(email_mod, "_get_provider", lambda: Ok())

def test_result_says_accepted_not_confirmed(monkeypatch):
    _ok_provider(monkeypatch, "msg-123")
    r = asyncio.run(email_mod.send_login_otp("a@organization.com", "111111"))
    assert r.accepted is True
    assert r.delivery_confirmed is False
    assert r.message_id == "msg-123"
    assert bool(r) is True            # old `if await send_...` style still works

def test_message_id_is_none_when_provider_has_none(monkeypatch):
    _ok_provider(monkeypatch, None)
    r = asyncio.run(email_mod.send_registration_otp("a@organization.com", "111111"))
    assert r.message_id is None

# ---- Fix 2: secrets hidden from repr ----
def test_repr_hides_secrets(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "S" * 40)
    monkeypatch.setenv("EMAIL_PASSWORD", "hunter2")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.topsecret")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:dbpass@h/db")
    text = repr(Settings()) + str(Settings())
    for secret in ("S" * 40, "hunter2", "SG.topsecret", "dbpass"):
        assert secret not in text


# ---- Fix 3: EMAIL_* names, SMTP_* fallback ----
def test_email_names_are_used(monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "mail.corp")
    monkeypatch.setenv("EMAIL_PORT", "2525")
    monkeypatch.setenv("EMAIL_USERNAME", "u")
    monkeypatch.setenv("EMAIL_PASSWORD", "p")
    s = Settings()
    assert (s.smtp_host, s.smtp_port, s.smtp_username, s.smtp_password) == ("mail.corp", 2525, "u", "p")

def test_old_smtp_names_still_work(monkeypatch):
    for k in ("EMAIL_HOST", "EMAIL_PORT", "EMAIL_USERNAME", "EMAIL_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SMTP_HOST", "old.corp")
    monkeypatch.setenv("SMTP_PORT", "25")
    assert (Settings().smtp_host, Settings().smtp_port) == ("old.corp", 25)


# ---- Fix 4: placeholder JWT key ----
def test_placeholder_jwt_key_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-to-a-long-random-string-of-at-least-32-chars")
    with pytest.raises(RuntimeError, match="placeholder"):
        Settings().validate()
