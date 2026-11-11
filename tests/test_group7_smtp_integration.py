"""
Integration tests: the real SmtpProvider talks to a real (local) SMTP server over real sockets.

These prove behaviour for success, bad credentials, refused recipients, server errors, dropped
connections, timeouts, unreachable hosts and TLS. They do NOT replace the one required test
against the team's approved SMTP sandbox with a real certificate.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import email
import email.policy
import logging
import shutil
import ssl
import subprocess

import pytest
from fake_smtp_server import FakeSmtpServer
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings

OTP = "482916"
PASSWORD = "s3cret-pw"


@pytest.fixture
def smtp(monkeypatch):
    """Factory: start a fake SMTP server and point the email service at it."""
    started = []

    def make(mode="accept", tls_mode="none", tls=None, timeout=1):
        server = FakeSmtpServer(mode=mode, tls=tls).start()
        started.append(server)
        env = {
            "ENVIRONMENT": "development", "EMAIL_PROVIDER": "smtp", "EMAIL_HOST": "127.0.0.1",
            "EMAIL_PORT": str(server.port), "EMAIL_TLS_MODE": tls_mode, "EMAIL_USERNAME": "mailer",
            "EMAIL_PASSWORD": PASSWORD, "EMAIL_FROM_ADDRESS": "noreply@example.com",
            "EMAIL_TIMEOUT_SECONDS": str(timeout),
        }
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setattr(email_mod, "settings", Settings())
        return server

    async def fast_sleep(_):
        pass

    monkeypatch.setattr(email_mod.asyncio, "sleep", fast_sleep)
    yield make
    for server in started:
        server.stop()


def send():
    return asyncio.run(email_mod.send_login_otp("alice@example.com", OTP))


def assert_failure(server, caplog, code, permanent, connections, expect_delivered=False):
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        with caplog.at_level(logging.DEBUG):
            send()
    assert (err.value.code, err.value.permanent) == (code, permanent)
    assert server.connections == connections
    assert (len(server.messages) > 0) is expect_delivered
    assert OTP not in caplog.text and PASSWORD not in caplog.text
    assert "alice@example.com" not in caplog.text


# ---------------------------------------------------------------- success
def test_success_delivers_the_configured_message(smtp):
    server = smtp()
    result = send()
    assert (result.accepted, result.provider, result.simulated, result.delivery_confirmed) == (True, "smtp", False, False)
    assert server.connections == 1 and len(server.messages) == 1 and server.auth_user == "mailer"

    msg = email.message_from_string(server.messages[0]["data"], policy=email.policy.default)
    assert "noreply@example.com" in msg["From"] and msg["To"] == "alice@example.com"
    assert "login" in msg["Subject"]
    assert OTP in msg.get_body(preferencelist=("plain",)).get_content()
    assert OTP in msg.get_body(preferencelist=("html",)).get_content()
    assert msg["Message-ID"] == result.message_id and result.message_id.endswith("@example.com>")


def test_registration_email_has_its_own_subject(smtp):
    server = smtp()
    asyncio.run(email_mod.send_registration_otp("alice@example.com", OTP))
    assert "register" in email.message_from_string(server.messages[0]["data"], policy=email.policy.default)["Subject"]


# ---------------------------------------------------------------- failures
def test_bad_credentials_fail_once(smtp, caplog):
    assert_failure(smtp("bad_auth"), caplog, "AUTH_FAILED", True, connections=1)


def test_recipient_rejected_fails_once(smtp, caplog):
    assert_failure(smtp("reject_rcpt"), caplog, "RECIPIENT_REFUSED", True, connections=1)


def test_temporary_recipient_error_is_retried(smtp, caplog):
    assert_failure(smtp("temp_rcpt"), caplog, "RECIPIENT_REFUSED", False, connections=3)


def test_message_rejected_by_server_fails_once(smtp, caplog):
    assert_failure(smtp("reject_data"), caplog, "PERMANENT_REJECTION", True, connections=1)


def test_dropped_connection_is_retried(smtp, caplog):
    assert_failure(smtp("drop"), caplog, "CONNECTION_FAILED", False, connections=3)


def test_unresponsive_server_times_out_and_is_retried(smtp, caplog):
    assert_failure(smtp("silent", timeout=1), caplog, "TIMEOUT", False, connections=3)


def test_unreachable_host_is_retried_and_reported(smtp, caplog):
    server = smtp()
    server.stop()                                   # nothing is listening any more
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        with caplog.at_level(logging.DEBUG):
            send()
    assert err.value.code in ("CONNECTION_FAILED", "TIMEOUT")   # Windows reports a timeout instead of "refused"
    assert err.value.permanent is False
    assert "attempt 3/3" in caplog.text


def test_starttls_required_but_not_offered_fails_closed(smtp, caplog):
    server = smtp(tls_mode="starttls")              # server does not offer STARTTLS
    assert_failure(server, caplog, "SERVER_UNSUPPORTED", True, connections=1)
    assert server.auth_user is None                 # credentials were never sent in clear text


# ---------------------------------------------------------------- real TLS (needs the openssl tool)
@pytest.fixture(scope="session")
def tls_files(tmp_path_factory):
    if not shutil.which("openssl"):
        pytest.skip("openssl command not available")
    folder = tmp_path_factory.mktemp("tls")
    cert, key = folder / "cert.pem", folder / "key.pem"
    done = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert),
         "-days", "2", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
        capture_output=True,
    )
    if done.returncode != 0:
        pytest.skip("openssl could not create a test certificate")
    return str(cert), str(key)


def test_untrusted_certificate_is_rejected_and_nothing_is_sent(smtp, tls_files, caplog):
    server = smtp(tls_mode="starttls", tls=tls_files)
    assert_failure(server, caplog, "TLS_FAILED", True, connections=1)
    assert server.auth_user is None and not server.tls_negotiated


def test_trusted_certificate_delivers_over_tls(smtp, tls_files, monkeypatch):
    real_default_context = ssl.create_default_context
    monkeypatch.setattr(email_mod.ssl, "create_default_context",
                        lambda *a, **k: real_default_context(cafile=tls_files[0]))
    server = smtp(tls_mode="starttls", tls=tls_files)
    result = send()
    assert result.accepted and server.tls_negotiated and server.auth_user == "mailer"
    assert OTP in server.messages[0]["data"]
