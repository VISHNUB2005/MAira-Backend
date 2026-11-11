"""
xsc_lib_a_email.py
------------------
Email dispatch service used by the auth modules to send OTP codes.

STABLE CONTRACT for other groups (Group 1 registration, Group 3 OTP/MFA):

    from xsc_lib.xsc_lib_app.xsc_lib_a_email import (
        email_service, EmailPurpose, EmailDeliveryError, EmailValidationError,
    )

    result = await email_service.send_otp(to_email, otp, EmailPurpose.LOGIN)   # or REGISTRATION

  Shortcuts that call the same code:
    await send_registration_otp(to_email, otp)      # Flow A
    await send_login_otp(to_email, otp)             # Flow B

  Returns SendResult. Raises:
    EmailValidationError  bad recipient / OTP format / purpose (caller bug; never retried)
    EmailDeliveryError    provider failure; has .code (sanitized) and .permanent

This module ONLY delivers email. It never generates, stores, expires or verifies OTPs (Group 3),
and it does not authenticate callers, rate-limit, or enforce the institutional-domain policy
(Group 1 / the API layer).

SendResult.accepted means the SMTP server ACCEPTED the message for delivery. It does NOT mean the
email reached the inbox; delivery_confirmed stays False (no provider webhooks exist).
SendResult.simulated is True for console/file/mock: nothing was sent to a real server.

Providers (EMAIL_PROVIDER): smtp (real) | mock (tests) | console, file (local development).
Amazon SES and SendGrid are not supported in this phase and are rejected at startup.
Blocking SMTP calls run in a worker thread so they never block the FastAPI event loop.
"""
from __future__ import annotations

import asyncio
import html
import logging
import random
import re
import smtplib
import ssl
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from xsc_lib.xsc_lib_app.xsc_lib_a_config import settings, validate_email_address

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2            # 3 attempts in total
_BACKOFF_CAP_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Errors and results
# ---------------------------------------------------------------------------
class EmailDeliveryError(RuntimeError):
    """The email could not be handed to the provider.

    .code       sanitized machine-readable reason (never contains secrets, OTPs or server text)
    .permanent  True if retrying cannot help (bad credentials, refused recipient, TLS failure...)
    """

    def __init__(self, message: str = "Unable to send email", code: str = "UNKNOWN",
                 permanent: bool = False):
        super().__init__(message)
        self.code = code
        self.permanent = permanent


class EmailValidationError(ValueError):
    """Recipient address, OTP format or purpose is invalid. Never contains the rejected value."""


@dataclass(frozen=True)
class SendResult:
    """Outcome of handing a message to a provider."""

    accepted: bool                       # the provider accepted it for delivery
    provider: str
    message_id: Optional[str] = None     # safe reference (our own Message-ID header for SMTP)
    delivery_confirmed: bool = False     # True only if a webhook later confirms inbox delivery
    simulated: bool = False              # True for console/file/mock: nothing real was sent

    def __bool__(self) -> bool:          # keeps `if await send_login_otp(...)` working
        return self.accepted


class EmailPurpose(str, Enum):
    REGISTRATION = "registration"
    LOGIN = "login"


# ---------------------------------------------------------------------------
# Input validation (generic messages: never echo the OTP or the address)
# ---------------------------------------------------------------------------
_OTP_RE = re.compile(r"^[A-Za-z0-9]{4,10}$")


def _validate_inputs(to_email: str, otp: str) -> str:
    try:
        address = validate_email_address(to_email)
    except ValueError:
        raise EmailValidationError("Invalid recipient email address") from None
    if not isinstance(otp, str) or not _OTP_RE.match(otp):
        raise EmailValidationError("Invalid OTP format")
    return address


# ---------------------------------------------------------------------------
# Message + templates
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EmailContent:
    subject: str
    text_body: str
    html_body: str


_HTML_LAYOUT = """\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 0;">
      <tr><td align="center">
        <table width="480" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;padding:32px;">
          <tr><td style="font-size:18px;font-weight:bold;color:#1a1a1a;">{app_name}</td></tr>
          <tr><td style="padding-top:16px;font-size:15px;color:#333333;line-height:1.5;">
            {intro}
          </td></tr>
          <tr><td align="center" style="padding:24px 0;">
            <span style="display:inline-block;font-size:32px;letter-spacing:8px;font-weight:bold;
                         color:#0b57d0;background:#eef3fd;padding:12px 24px;border-radius:6px;">
              {otp}
            </span>
          </td></tr>
          <tr><td style="font-size:13px;color:#666666;line-height:1.5;">
            This code expires in <b>{expiry} minutes</b> and can be used only once.<br>
            {warning}
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""


def _render(subject: str, intro: str, warning: str, otp: str) -> EmailContent:
    expiry = settings.otp_expiry_minutes
    app_name = settings.app_name

    text_body = (
        f"{app_name}\n\n"
        f"{intro}\n\n"
        f"Your verification code: {otp}\n\n"
        f"This code expires in {expiry} minutes and can be used only once.\n"
        f"{warning}\n"
    )
    html_body = _HTML_LAYOUT.format(
        app_name=html.escape(app_name),
        intro=html.escape(intro),
        otp=html.escape(otp),
        expiry=expiry,
        warning=html.escape(warning),
    )
    return EmailContent(subject=subject, text_body=text_body, html_body=html_body)


def build_registration_email(otp: str) -> EmailContent:
    return _render(
        subject=f"{settings.app_name}: verify your email to register",
        intro="Use the code below to verify your email address and continue creating your account.",
        warning="If you did not try to register, you can ignore this email.",
        otp=otp,
    )


def build_login_email(otp: str) -> EmailContent:
    return _render(
        subject=f"{settings.app_name}: your login verification code",
        intro="Use the code below to complete your sign-in.",
        warning="If this wasn't you, change your password immediately and contact your administrator.",
        otp=otp,
    )


_BUILDERS = {
    EmailPurpose.REGISTRATION: build_registration_email,
    EmailPurpose.LOGIN: build_login_email,
}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
class EmailProvider(ABC):
    simulated: bool = False      # True when nothing is sent to a real server

    @abstractmethod
    def send(self, to_email: str, content: EmailContent) -> Optional[str]:
        """Send synchronously. Return a safe message reference if there is one.
        Raise any exception on failure."""


class ConsoleProvider(EmailProvider):
    """Local development only: prints the email (INCLUDING the OTP) instead of sending it."""

    simulated = True

    def send(self, to_email: str, content: EmailContent) -> Optional[str]:
        logger.warning(
            "[DEV EMAIL] to=%s subject=%s\n%s", to_email, content.subject, content.text_body
        )
        return None


class FileProvider(EmailProvider):
    """Local development: saves each email as .html and .txt files you can open in a browser.

    Files go to EMAIL_OUTBOX_DIR (default ./outbox). latest.html / latest.txt always hold the
    newest email. Nothing is sent over the network.
    """

    simulated = True

    def send(self, to_email: str, content: EmailContent) -> Optional[str]:
        folder = Path(settings.email_outbox_dir)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        name = f"{stamp}_{re.sub(r'[^A-Za-z0-9]+', '_', to_email)[:60]}"
        text = f"To: {to_email}\nSubject: {content.subject}\n\n{content.text_body}"
        for base in (name, "latest"):
            (folder / f"{base}.html").write_text(content.html_body, encoding="utf-8")
            (folder / f"{base}.txt").write_text(text, encoding="utf-8")
        logger.warning("[DEV EMAIL FILE] saved to %s", (folder / "latest.html").resolve())
        return name


class MockProvider(EmailProvider):
    """Test mode (Group 9): nothing is sent, messages are kept in MockProvider.outbox.

    Thread-safe: message ids are unique even when many threads send at once.
    """

    simulated = True
    outbox: List[Dict[str, str]] = []
    _lock = threading.Lock()
    _counter = 0

    def send(self, to_email: str, content: EmailContent) -> Optional[str]:
        with MockProvider._lock:
            MockProvider._counter += 1
            message_id = f"mock-{MockProvider._counter}"
            MockProvider.outbox.append(
                {"id": message_id, "to": to_email, "subject": content.subject,
                 "text": content.text_body, "html": content.html_body}
            )
        return message_id

    @staticmethod
    def clear() -> None:
        with MockProvider._lock:
            MockProvider.outbox.clear()
            MockProvider._counter = 0


def _build_mime(to_email: str, content: EmailContent) -> EmailMessage:
    sender = settings.email_from_address
    msg = EmailMessage()
    msg["Subject"] = content.subject
    msg["From"] = formataddr((settings.email_from_name, sender))
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid(domain=sender.partition("@")[2] or None)
    msg.set_content(content.text_body)
    msg.add_alternative(content.html_body, subtype="html")
    return msg


class SmtpProvider(EmailProvider):
    """Real delivery over SMTP with certificate and hostname verification.

    EMAIL_TLS_MODE=starttls  connect, then upgrade with STARTTLS (fails closed if unsupported)
    EMAIL_TLS_MODE=ssl       implicit TLS (usually port 465)
    EMAIL_TLS_MODE=none      plain text; allowed in development/test only (enforced by config)
    """

    def send(self, to_email: str, content: EmailContent) -> Optional[str]:
        msg = _build_mime(to_email, content)
        mode = settings.email_tls_mode
        context = ssl.create_default_context()          # verifies certificate AND hostname
        timeout = settings.email_timeout_seconds

        if mode == "ssl":
            factory, extra = smtplib.SMTP_SSL, {"context": context}
        else:
            factory, extra = smtplib.SMTP, {}

        with factory(settings.smtp_host, settings.smtp_port, timeout=timeout, **extra) as server:
            if mode == "starttls":
                server.ehlo()
                server.starttls(context=context)        # raises SMTPNotSupportedError if absent
                server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return msg["Message-ID"]


_PROVIDERS = {
    "smtp": SmtpProvider,
    "mock": MockProvider,
    "console": ConsoleProvider,
    "file": FileProvider,
}


def _get_provider() -> EmailProvider:
    return _PROVIDERS[settings.email_provider]()


# ---------------------------------------------------------------------------
# Error classification (sanitized: only codes, never server text)
# ---------------------------------------------------------------------------
def _mask_email(email: str) -> str:
    """a***@organization.com  - so logs never contain full addresses."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def _is_permanent_failure(exc: Exception) -> bool:
    """True for errors that retrying cannot fix."""
    if isinstance(exc, (ssl.SSLError, smtplib.SMTPNotSupportedError)):
        return True                                           # TLS problems fail closed
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        # smtplib raises this for 4xx too; permanent only if EVERY recipient got a 5xx.
        return all(500 <= code < 600 for code, _ in exc.recipients.values())
    if isinstance(exc, smtplib.SMTPResponseException):       # includes auth / sender / data errors
        return 500 <= exc.smtp_code < 600
    return False


def _error_code(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPServerDisconnected) and isinstance(exc.__context__, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, ssl.SSLError):
        return "TLS_FAILED"
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        return "SERVER_UNSUPPORTED"
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "AUTH_FAILED"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "RECIPIENT_REFUSED"
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "SENDER_REFUSED"
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, smtplib.SMTPResponseException):
        return "PERMANENT_REJECTION" if 500 <= exc.smtp_code < 600 else "TEMPORARY_REJECTION"
    if isinstance(exc, (smtplib.SMTPException, OSError)):
        return "CONNECTION_FAILED"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
async def _dispatch(to_email: str, content: EmailContent,
                    provider: Optional[EmailProvider] = None,
                    retries: int = _MAX_RETRIES) -> SendResult:
    provider = provider or _get_provider()
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            message_id = await asyncio.to_thread(provider.send, to_email, content)
            logger.info(
                "Email accepted to %s (provider=%s simulated=%s)",
                _mask_email(to_email), settings.email_provider, provider.simulated,
            )
            return SendResult(
                accepted=True, provider=settings.email_provider,
                message_id=message_id, simulated=provider.simulated,
            )
        except Exception as exc:  # providers raise many different types
            last_exc = exc
            code = _error_code(exc)
            if _is_permanent_failure(exc):
                logger.error(
                    "Email to %s failed permanently: code=%s (%s), not retrying",
                    _mask_email(to_email), code, type(exc).__name__,
                )
                break
            logger.warning(
                "Email attempt %d/%d to %s failed: code=%s (%s)",
                attempt + 1, retries + 1, _mask_email(to_email), code, type(exc).__name__,
            )
            if attempt < retries:
                # Bounded exponential backoff with jitter.
                delay = min(_BACKOFF_CAP_SECONDS, 2 ** attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)

    assert last_exc is not None
    # `from None`: the original exception text (server replies, hosts) must not reach callers or traces.
    raise EmailDeliveryError(
        "Unable to send email", code=_error_code(last_exc),
        permanent=_is_permanent_failure(last_exc),
    ) from None


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------
class EmailService:
    """The one stable async entry point other groups use. Delivery only."""

    def __init__(self, provider: Optional[EmailProvider] = None):
        self._provider = provider          # None = pick from settings at send time

    async def send_otp(self, to_email: str, otp: str,
                       purpose: Union[EmailPurpose, str]) -> SendResult:
        try:
            purpose = EmailPurpose(purpose)
        except ValueError:
            raise EmailValidationError("Unknown email purpose") from None
        address = _validate_inputs(to_email, otp)
        content = _BUILDERS[purpose](otp)
        return await _dispatch(address, content, self._provider)


email_service = EmailService()


async def send_registration_otp(to_email: str, otp: str) -> SendResult:
    """Registration stage: OTP to verify a pre-approved email (Flow A, step 1)."""
    return await email_service.send_otp(to_email, otp, EmailPurpose.REGISTRATION)


async def send_login_otp(to_email: str, otp: str) -> SendResult:
    """Login MFA stage: OTP after email + password pass (Flow B, step 2)."""
    return await email_service.send_otp(to_email, otp, EmailPurpose.LOGIN)
