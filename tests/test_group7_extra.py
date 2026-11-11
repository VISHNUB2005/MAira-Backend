import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import logging
from unittest.mock import patch

import pytest
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app import xsc_lib_a_secrets as secrets_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings

def test_reads_docker_secret_file(monkeypatch, tmp_path):
    (tmp_path / "my_file_secret").write_text("from-file\n")
    monkeypatch.setattr(secrets_mod, "DOCKER_SECRETS_DIR", tmp_path)
    monkeypatch.delenv("MY_FILE_SECRET", raising=False)
    assert secrets_mod.get_secret("MY_FILE_SECRET") == "from-file"

def test_env_var_beats_secret_file(monkeypatch, tmp_path):
    (tmp_path / "my_secret").write_text("file")
    monkeypatch.setattr(secrets_mod, "DOCKER_SECRETS_DIR", tmp_path)
    monkeypatch.setenv("MY_SECRET", "env")
    assert secrets_mod.get_secret("MY_SECRET") == "env"

def test_default_is_used_when_missing(monkeypatch):
    monkeypatch.delenv("NOT_SET_ANYWHERE", raising=False)
    assert secrets_mod.get_secret("NOT_SET_ANYWHERE", default="d") == "d"

def test_domain_list_is_parsed_and_trimmed(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "a.com, b.com ,")
    assert Settings().allowed_email_domains == ["a.com", "b.com"]

def test_smtp_requires_credentials(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    with pytest.raises(RuntimeError, match="EMAIL_USERNAME"):
        Settings().validate()

def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "carrier-pigeon")
    with pytest.raises(RuntimeError, match="Unknown EMAIL_PROVIDER"):
        Settings().validate()

def test_mime_message_has_text_and_html():
    msg = email_mod._build_mime("a@organization.com", email_mod.build_login_email("123456"))
    assert msg.is_multipart()
    assert msg["To"] == "a@organization.com"

def test_smtp_provider_sends_message():
    with patch.object(email_mod.smtplib, "SMTP") as smtp_cls:
        server = smtp_cls.return_value.__enter__.return_value
        email_mod.SmtpProvider().send("a@organization.com", email_mod.build_login_email("123456"))
        server.send_message.assert_called_once()
        sent = server.send_message.call_args[0][0]
        assert "123456" in sent.get_body(preferencelist=("plain",)).get_content()

def test_mask_email():
    assert email_mod._mask_email("alice@organization.com") == "a***@organization.com"

def test_success_logs_contain_no_otp_or_full_email(monkeypatch, caplog):
    class Ok(email_mod.EmailProvider):
        def send(self, to_email, content):
            pass
    monkeypatch.setattr(email_mod, "_get_provider", lambda: Ok())
    with caplog.at_level(logging.DEBUG):
        asyncio.run(email_mod.send_login_otp("alice@organization.com", "987654"))
    assert "987654" not in caplog.text
    assert "alice@organization.com" not in caplog.text

def test_failure_logs_do_not_leak_provider_details(monkeypatch, caplog):
    class Dead(email_mod.EmailProvider):
        def send(self, to_email, content):
            raise ConnectionError("password=hunter2")
    async def fast_sleep(_):
        pass
    monkeypatch.setattr(email_mod, "_get_provider", lambda: Dead())
    monkeypatch.setattr(email_mod.asyncio, "sleep", fast_sleep)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(email_mod.EmailDeliveryError):
            asyncio.run(email_mod.send_registration_otp("alice@organization.com", "987654"))
    assert "hunter2" not in caplog.text
    assert "987654" not in caplog.text
