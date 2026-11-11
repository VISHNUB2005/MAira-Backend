"""
Tests for the technical-review checklist (configuration, secrets, email service, error handling).
Real-socket SMTP tests are in test_group7_smtp_integration.py.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import asyncio
import smtplib
import ssl
import sys
import traceback
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from xsc_lib.xsc_lib_app import xsc_lib_a_config as config_mod
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app import xsc_lib_a_secrets as secrets_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings, validate_email_address

VALID_SMTP = {
    "ENVIRONMENT": "development",
    "EMAIL_PROVIDER": "smtp",
    "EMAIL_HOST": "smtp.example.com",
    "EMAIL_PORT": "587",
    "EMAIL_USERNAME": "mailer",
    "EMAIL_PASSWORD": "pw-not-real",
    "EMAIL_FROM_ADDRESS": "noreply@example.com",
}


def smtp_env(monkeypatch, **overrides):
    for key, value in {**VALID_SMTP, **overrides}.items():
        monkeypatch.setenv(key, value)


# ===================================================================== configuration
def test_valid_smtp_config_passes(monkeypatch):
    smtp_env(monkeypatch)
    Settings().validate()


@pytest.mark.parametrize("env", ["staging", "production"])
def test_valid_smtp_config_passes_in_staging_and_production(monkeypatch, env):
    smtp_env(monkeypatch, ENVIRONMENT=env)
    Settings().validate()


@pytest.mark.parametrize("var", ["EMAIL_HOST", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_FROM_ADDRESS"])
def test_missing_smtp_setting_is_reported_by_name(monkeypatch, var):
    smtp_env(monkeypatch)
    monkeypatch.delenv(var)
    with pytest.raises(RuntimeError, match=f"{var} is not set"):
        Settings().validate()


@pytest.mark.parametrize("blank", ["", "   "])
@pytest.mark.parametrize("var", ["EMAIL_HOST", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_FROM_ADDRESS"])
def test_empty_smtp_setting_is_reported_separately_from_missing(monkeypatch, var, blank):
    smtp_env(monkeypatch, **{var: blank})
    with pytest.raises(RuntimeError, match=f"{var} is set but empty"):
        Settings().validate()


def test_no_default_smtp_host_or_credentials(monkeypatch):
    for name in VALID_SMTP:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    with pytest.raises(RuntimeError) as err:
        Settings().validate()
    for var in ("EMAIL_HOST", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_FROM_ADDRESS"):
        assert f"{var} is not set" in str(err.value)


def test_no_default_jwt_key(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY")
    with pytest.raises(secrets_mod.MissingSecretError):
        Settings()


def test_invalid_sender_format_rejected(monkeypatch):
    smtp_env(monkeypatch, EMAIL_FROM_ADDRESS="not-an-email")
    with pytest.raises(RuntimeError, match="EMAIL_FROM_ADDRESS is not a valid email address"):
        Settings().validate()


def test_config_errors_never_contain_secret_values(monkeypatch):
    smtp_env(monkeypatch, EMAIL_PASSWORD="SuperSecret99", EMAIL_PORT="70000")
    monkeypatch.delenv("EMAIL_USERNAME")
    with pytest.raises(RuntimeError) as err:
        Settings().validate()
    assert "SuperSecret99" not in str(err.value)


def test_non_numeric_port_gives_clear_error_without_value(monkeypatch):
    smtp_env(monkeypatch, EMAIL_PORT="abc-secret")
    with pytest.raises(RuntimeError, match="EMAIL_PORT must be a whole number") as err:
        Settings()
    assert "abc-secret" not in str(err.value)


@pytest.mark.parametrize("port", ["0", "-1", "65536", "99999"])
def test_port_out_of_range_rejected(monkeypatch, port):
    smtp_env(monkeypatch, EMAIL_PORT=port)
    with pytest.raises(RuntimeError, match="EMAIL_PORT must be between 1 and 65535"):
        Settings().validate()


@pytest.mark.parametrize("timeout", ["0", "-5", "121", "9999"])
def test_timeout_out_of_range_rejected(monkeypatch, timeout):
    smtp_env(monkeypatch, EMAIL_TIMEOUT_SECONDS=timeout)
    with pytest.raises(RuntimeError, match="EMAIL_TIMEOUT_SECONDS must be between 1 and 120"):
        Settings().validate()


def test_non_numeric_timeout_rejected(monkeypatch):
    smtp_env(monkeypatch, EMAIL_TIMEOUT_SECONDS="soon")
    with pytest.raises(RuntimeError, match="EMAIL_TIMEOUT_SECONDS must be a whole number"):
        Settings()


@pytest.mark.parametrize("provider", ["ses", "sendgrid"])
def test_unsupported_providers_are_rejected_explicitly(monkeypatch, provider):
    monkeypatch.setenv("EMAIL_PROVIDER", provider)
    with pytest.raises(RuntimeError, match="not supported in this phase"):
        Settings().validate()


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "carrier-pigeon")
    with pytest.raises(RuntimeError, match="Unknown EMAIL_PROVIDER"):
        Settings().validate()


@pytest.mark.parametrize("env", ["prod", "dev", "Production", "local"])
def test_unknown_environment_rejected(monkeypatch, env):
    smtp_env(monkeypatch, ENVIRONMENT=env)
    with pytest.raises(RuntimeError, match="ENVIRONMENT must be one of"):
        Settings().validate()


def test_invalid_tls_mode_rejected(monkeypatch):
    smtp_env(monkeypatch, EMAIL_TLS_MODE="maybe")
    with pytest.raises(RuntimeError, match="EMAIL_TLS_MODE must be starttls, ssl or none"):
        Settings().validate()


@pytest.mark.parametrize("env", ["staging", "production"])
def test_plain_text_smtp_blocked_outside_dev(monkeypatch, env):
    smtp_env(monkeypatch, ENVIRONMENT=env, EMAIL_TLS_MODE="none")
    with pytest.raises(RuntimeError, match="EMAIL_TLS_MODE=none is only allowed"):
        Settings().validate()


def test_plain_text_smtp_allowed_in_development(monkeypatch):
    smtp_env(monkeypatch, EMAIL_TLS_MODE="none")
    Settings().validate()


@pytest.mark.parametrize("name,value", [("OTP_LENGTH", "3"), ("OTP_LENGTH", "11"),
                                        ("OTP_EXPIRY_MINUTES", "0"), ("OTP_MAX_ATTEMPTS", "0")])
def test_otp_settings_bounds(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        Settings().validate()


# ===================================================================== secrets
def test_env_beats_name_file_beats_docker_secret(monkeypatch, tmp_path):
    named = tmp_path / "named.txt"
    named.write_text("from-name-file\n")
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (docker_dir / "my_precedence_secret").write_text("from-docker")
    monkeypatch.setattr(secrets_mod, "DOCKER_SECRETS_DIR", docker_dir)

    monkeypatch.delenv("MY_PRECEDENCE_SECRET", raising=False)
    monkeypatch.delenv("MY_PRECEDENCE_SECRET_FILE", raising=False)
    assert secrets_mod.get_secret("MY_PRECEDENCE_SECRET") == "from-docker"

    monkeypatch.setenv("MY_PRECEDENCE_SECRET_FILE", str(named))
    assert secrets_mod.get_secret("MY_PRECEDENCE_SECRET") == "from-name-file"

    monkeypatch.setenv("MY_PRECEDENCE_SECRET", "from-env")
    assert secrets_mod.get_secret("MY_PRECEDENCE_SECRET") == "from-env"


def test_name_file_pointing_nowhere_fails_clearly(monkeypatch, tmp_path):
    monkeypatch.delenv("MY_FILE_SECRET", raising=False)
    monkeypatch.setenv("MY_FILE_SECRET_FILE", str(tmp_path / "missing.txt"))
    with pytest.raises(secrets_mod.SecretFileError, match="MY_FILE_SECRET_FILE points to a file that does not exist"):
        secrets_mod.get_secret("MY_FILE_SECRET")


def test_unreadable_secret_file_fails_clearly_without_details(monkeypatch, tmp_path):
    secret_file = tmp_path / "locked.txt"
    secret_file.write_text("top-secret-value")
    monkeypatch.delenv("MY_LOCKED_SECRET", raising=False)
    monkeypatch.setenv("MY_LOCKED_SECRET_FILE", str(secret_file))

    def deny(self, *args, **kwargs):
        raise PermissionError(f"permission denied: {self}")

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(secrets_mod.SecretFileError, match="cannot be read") as err:
        secrets_mod.get_secret("MY_LOCKED_SECRET")
    assert str(tmp_path) not in str(err.value)
    assert "top-secret-value" not in str(err.value)


def test_empty_secret_file_fails_clearly(monkeypatch, tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n")
    monkeypatch.delenv("MY_EMPTY_SECRET", raising=False)
    monkeypatch.setenv("MY_EMPTY_SECRET_FILE", str(empty))
    assert secrets_mod.secret_status("MY_EMPTY_SECRET") == "empty"
    with pytest.raises(secrets_mod.MissingSecretError, match="not set or is empty"):
        secrets_mod.get_secret("MY_EMPTY_SECRET", required=True)


def test_secret_status_values(monkeypatch):
    monkeypatch.delenv("STATUS_PROBE", raising=False)
    assert secrets_mod.secret_status("STATUS_PROBE") == "unset"
    monkeypatch.setenv("STATUS_PROBE", "")
    assert secrets_mod.secret_status("STATUS_PROBE") == "empty"
    monkeypatch.setenv("STATUS_PROBE", "x")
    assert secrets_mod.secret_status("STATUS_PROBE") == "set"


def test_secrets_never_appear_in_settings_text(monkeypatch):
    smtp_env(monkeypatch, EMAIL_PASSWORD="hunter2-hunter2", EMAIL_USERNAME="very-secret-user")
    monkeypatch.setenv("JWT_SECRET_KEY", "J" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:dbpassword@h/db")
    text = repr(Settings()) + str(Settings())
    for secret in ("hunter2-hunter2", "very-secret-user", "J" * 40, "dbpassword"):
        assert secret not in text


# ===================================================================== email address validation
def test_strict_validator_when_library_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "email_validator", None)      # makes `import` fail
    assert validate_email_address("alice@organization.com") == "alice@organization.com"
    assert validate_email_address("  A.B+tag@Sub.Example.COM ") == "A.B+tag@sub.example.com"
    for bad in ["a@b", ".a@x.com", "a.@x.com", "a..b@x.com", "a@-x.com", "a@x-.com", "a@x.com.",
                "a@1.2", "a b@x.com", "a@@x.com", "@x.com", "a@", "", "   ", None, 123,
                "a@x.com\r\nBcc: e@x.com", "x" * 65 + "@x.com", "a@" + "x" * 250 + ".com"]:
        with pytest.raises(ValueError, match="invalid email address"):
            validate_email_address(bad)


def test_validator_uses_email_validator_library_when_installed(monkeypatch):
    stub = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        pass

    def validate_email(address, check_deliverability=True):
        assert check_deliverability is False          # must never do DNS lookups
        if "bad" in address:
            raise EmailNotValidError("secret detail about " + address)
        return types.SimpleNamespace(normalized="Alice@example.com", email="old@example.com")

    stub.EmailNotValidError, stub.validate_email = EmailNotValidError, validate_email
    monkeypatch.setitem(sys.modules, "email_validator", stub)
    assert validate_email_address("ALICE@Example.com") == "Alice@example.com"
    with pytest.raises(ValueError) as err:
        validate_email_address("bad@example.com")
    assert str(err.value) == "invalid email address"          # library text is not passed on


def test_validator_supports_old_library_without_normalized(monkeypatch):
    stub = types.ModuleType("email_validator")
    stub.EmailNotValidError = type("EmailNotValidError", (ValueError,), {})
    stub.validate_email = lambda address, check_deliverability=True: types.SimpleNamespace(email="old@example.com")
    monkeypatch.setitem(sys.modules, "email_validator", stub)
    assert validate_email_address("x@example.com") == "old@example.com"


def test_real_email_validator_library_if_installed():
    pytest.importorskip("email_validator")
    assert validate_email_address("alice@organization.com") == "alice@organization.com"
    for bad in ["a@b", "user@@x.com", "a b@x.com", "", "a@x.com\r\nBcc: e@x.com"]:
        with pytest.raises(ValueError):
            validate_email_address(bad)


# ===================================================================== service contract
@pytest.fixture
def mock_outbox(monkeypatch):
    monkeypatch.setattr(email_mod, "_get_provider", lambda: email_mod.MockProvider())
    email_mod.MockProvider.clear()
    return email_mod.MockProvider.outbox


@pytest.mark.parametrize("purpose,word", [("registration", "register"), (email_mod.EmailPurpose.REGISTRATION, "register"),
                                          ("login", "login"), (email_mod.EmailPurpose.LOGIN, "login")])
def test_service_purpose_selects_template(mock_outbox, purpose, word):
    result = asyncio.run(email_mod.email_service.send_otp("a@organization.com", "123456", purpose))
    assert result.accepted and word in mock_outbox[-1]["subject"]


def test_unknown_purpose_rejected(mock_outbox):
    with pytest.raises(email_mod.EmailValidationError, match="Unknown email purpose"):
        asyncio.run(email_mod.email_service.send_otp("a@organization.com", "123456", "password-reset"))
    assert mock_outbox == []


def test_shortcut_functions_use_the_same_service(mock_outbox):
    asyncio.run(email_mod.send_registration_otp("a@organization.com", "111111"))
    asyncio.run(email_mod.send_login_otp("a@organization.com", "222222"))
    assert "register" in mock_outbox[0]["subject"] and "login" in mock_outbox[1]["subject"]


def test_service_accepts_an_injected_provider():
    provider = email_mod.MockProvider()
    email_mod.MockProvider.clear()
    service = email_mod.EmailService(provider=provider)
    asyncio.run(service.send_otp("a@organization.com", "123456", "login"))
    assert len(email_mod.MockProvider.outbox) == 1


def test_invalid_input_errors_do_not_echo_otp_or_address(mock_outbox):
    with pytest.raises(email_mod.EmailValidationError) as bad_otp:
        asyncio.run(email_mod.send_login_otp("a@organization.com", "12 34-secret"))
    assert "12 34-secret" not in str(bad_otp.value) and "12 34-secret" not in repr(bad_otp.value.args)
    with pytest.raises(email_mod.EmailValidationError) as bad_addr:
        asyncio.run(email_mod.send_login_otp("secret person@x", "123456"))
    assert "secret person" not in str(bad_addr.value)
    assert mock_outbox == []


def test_result_never_contains_the_otp(mock_outbox):
    result = asyncio.run(email_mod.send_login_otp("a@organization.com", "918273"))
    assert "918273" not in repr(result)


def test_simulated_flag_and_semantics(mock_outbox):
    result = asyncio.run(email_mod.send_login_otp("a@organization.com", "123456"))
    assert (result.accepted, result.simulated, result.delivery_confirmed) == (True, True, False)


def test_console_and_file_providers_are_marked_simulated():
    assert email_mod.ConsoleProvider.simulated and email_mod.FileProvider.simulated
    assert email_mod.MockProvider.simulated and not email_mod.SmtpProvider.simulated


# ===================================================================== mock provider
def test_mock_ids_unique_under_concurrency():
    email_mod.MockProvider.clear()
    content = email_mod.build_login_email("123456")
    with ThreadPoolExecutor(32) as pool:
        ids = list(pool.map(lambda _: email_mod.MockProvider().send("a@x.com", content), range(3000)))
    assert len(set(ids)) == 3000 and len(email_mod.MockProvider.outbox) == 3000
    assert {m["id"] for m in email_mod.MockProvider.outbox} == set(ids)


def test_mock_clear_resets_outbox_and_ids():
    content = email_mod.build_login_email("123456")
    email_mod.MockProvider().send("a@x.com", content)
    email_mod.MockProvider.clear()
    assert email_mod.MockProvider.outbox == []
    assert email_mod.MockProvider().send("b@x.com", content) == "mock-1"


# ===================================================================== SMTP TLS behaviour
@pytest.fixture
def smtp_settings(monkeypatch):
    def apply(**overrides):
        smtp_env(monkeypatch, **overrides)
        monkeypatch.setattr(email_mod, "settings", Settings())
    return apply


def _send_with_mock_smtp(factory_name):
    content = email_mod.build_login_email("123456")
    with patch.object(email_mod.smtplib, factory_name) as factory:
        server = factory.return_value.__enter__.return_value
        email_mod.SmtpProvider().send("alice@example.com", content)
    return factory, server


def test_starttls_uses_verifying_context_in_the_right_order(smtp_settings):
    smtp_settings(EMAIL_TLS_MODE="starttls")
    factory, server = _send_with_mock_smtp("SMTP")
    names = [c[0] for c in server.mock_calls]
    assert names == ["ehlo", "starttls", "ehlo", "login", "send_message"]
    context = server.starttls.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True
    assert factory.call_args.kwargs["timeout"] == 15


def test_ssl_mode_uses_verifying_context_and_no_starttls(smtp_settings):
    smtp_settings(EMAIL_TLS_MODE="ssl", EMAIL_PORT="465", EMAIL_TIMEOUT_SECONDS="7")
    factory, server = _send_with_mock_smtp("SMTP_SSL")
    context = factory.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True
    assert factory.call_args.kwargs["timeout"] == 7
    assert not server.starttls.called and server.login.called


def test_none_mode_never_starts_tls(smtp_settings):
    smtp_settings(EMAIL_TLS_MODE="none")
    _, server = _send_with_mock_smtp("SMTP")
    assert not server.starttls.called and server.send_message.called


def test_smtp_message_uses_configured_sender_and_own_message_id(smtp_settings):
    smtp_settings(EMAIL_FROM_ADDRESS="noreply@maira.example", EMAIL_FROM_NAME="MAira")
    _, server = _send_with_mock_smtp("SMTP")
    msg = server.send_message.call_args[0][0]
    assert "noreply@maira.example" in msg["From"] and msg["To"] == "alice@example.com"
    assert msg["Message-ID"].endswith("@maira.example>")


# ===================================================================== error classification
def _disconnected_after_timeout():
    try:
        try:
            raise TimeoutError()
        except OSError:
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
    except smtplib.SMTPServerDisconnected as exc:
        return exc


CASES = [
    (smtplib.SMTPAuthenticationError(535, b"bad"), "AUTH_FAILED", True),
    (smtplib.SMTPAuthenticationError(454, b"temporary"), "AUTH_FAILED", False),
    (smtplib.SMTPRecipientsRefused({"a@x.com": (550, b"no")}), "RECIPIENT_REFUSED", True),
    (smtplib.SMTPRecipientsRefused({"a@x.com": (451, b"later")}), "RECIPIENT_REFUSED", False),
    (smtplib.SMTPSenderRefused(553, b"no", "s@x.com"), "SENDER_REFUSED", True),
    (smtplib.SMTPResponseException(554, b"no"), "PERMANENT_REJECTION", True),
    (smtplib.SMTPResponseException(451, b"later"), "TEMPORARY_REJECTION", False),
    (smtplib.SMTPNotSupportedError("no starttls"), "SERVER_UNSUPPORTED", True),
    (ssl.SSLCertVerificationError("bad cert"), "TLS_FAILED", True),
    (ssl.SSLError("handshake"), "TLS_FAILED", True),
    (TimeoutError(), "TIMEOUT", False),
    (_disconnected_after_timeout(), "TIMEOUT", False),
    (ConnectionRefusedError(), "CONNECTION_FAILED", False),
    (smtplib.SMTPServerDisconnected("gone"), "CONNECTION_FAILED", False),
    (ValueError("odd"), "UNKNOWN", False),
]


@pytest.mark.parametrize("exc,code,permanent", CASES)
def test_error_codes_and_retry_classification(exc, code, permanent):
    assert email_mod._error_code(exc) == code
    assert email_mod._is_permanent_failure(exc) is permanent


def _failing_provider(monkeypatch, exc, calls, sleeps=None):
    class Failing(email_mod.EmailProvider):
        def send(self, to_email, content):
            calls.append(1)
            raise exc

    async def record_sleep(delay):
        if sleeps is not None:
            sleeps.append(delay)

    monkeypatch.setattr(email_mod, "_get_provider", lambda: Failing())
    monkeypatch.setattr(email_mod.asyncio, "sleep", record_sleep)


def test_delivery_error_carries_only_a_sanitized_code(monkeypatch):
    calls = []
    otp, address = "246810", "alice@example.com"      # variables: the values must not appear in source lines
    _failing_provider(monkeypatch, smtplib.SMTPAuthenticationError(535, b"password=hunter2 host=internal.mail"), calls)
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        asyncio.run(email_mod.send_login_otp(address, otp))
    exc = err.value
    assert (exc.code, exc.permanent, str(exc)) == ("AUTH_FAILED", True, "Unable to send email")
    assert exc.__suppress_context__ is True and exc.__cause__ is None
    trace = "".join(traceback.format_exception(exc))
    for leaked in ("hunter2", "internal.mail", otp, address):
        assert leaked not in trace and leaked not in repr(exc)
    assert len(calls) == 1


def test_transient_errors_are_retried_a_bounded_number_of_times_with_jitter(monkeypatch):
    calls, sleeps = [], []
    _failing_provider(monkeypatch, TimeoutError(), calls, sleeps)
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        asyncio.run(email_mod.send_login_otp("alice@example.com", "246810"))
    assert len(calls) == 3 and len(sleeps) == 2
    assert 1.0 <= sleeps[0] <= 1.5 and 2.0 <= sleeps[1] <= 2.5
    assert (err.value.code, err.value.permanent) == ("TIMEOUT", False)


def test_backoff_jitter_actually_varies(monkeypatch):
    seen = set()
    for _ in range(8):
        calls, sleeps = [], []
        _failing_provider(monkeypatch, TimeoutError(), calls, sleeps)
        with pytest.raises(email_mod.EmailDeliveryError):
            asyncio.run(email_mod.send_login_otp("alice@example.com", "246810"))
        seen.add(round(sleeps[0], 4))
    assert len(seen) > 1


def test_temporary_recipient_refusal_is_retried(monkeypatch):
    calls = []
    _failing_provider(monkeypatch, smtplib.SMTPRecipientsRefused({"a@x.com": (451, b"later")}), calls)
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        asyncio.run(email_mod.send_login_otp("alice@example.com", "246810"))
    assert len(calls) == 3 and err.value.permanent is False


def test_tls_failures_fail_closed_without_retry(monkeypatch):
    calls = []
    _failing_provider(monkeypatch, ssl.SSLCertVerificationError("certificate verify failed"), calls)
    with pytest.raises(email_mod.EmailDeliveryError) as err:
        asyncio.run(email_mod.send_login_otp("alice@example.com", "246810"))
    assert len(calls) == 1 and (err.value.code, err.value.permanent) == ("TLS_FAILED", True)
