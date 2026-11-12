"""Email Dispatch Service."""

import asyncio
import html
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("maira.email")
settings = get_settings()


@dataclass
class EmailContent:
    subject: str
    text_body: str
    html_body: Optional[str] = None


@dataclass
class SendResult:
    accepted: bool
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class MockEmailProvider:
    """Mock provider for testing and development."""
    outbox: List[Dict[str, Any]] = []

    @classmethod
    def clear(cls) -> None:
        cls.outbox.clear()

    @classmethod
    def get_latest_for(cls, email: str) -> Optional[Dict[str, Any]]:
        for msg in reversed(cls.outbox):
            if msg["to"].lower() == email.lower():
                return msg
        return None

    @classmethod
    async def send(cls, to_email: str, content: EmailContent) -> SendResult:
        msg_id = f"mock-msg-{len(cls.outbox) + 1}"
        cls.outbox.append({
            "to": to_email,
            "subject": content.subject,
            "text": content.text_body,
            "html": content.html_body,
            "message_id": msg_id,
        })
        logger.info(f"[MOCK EMAIL] Sent to {to_email}: subject='{content.subject}'")
        return SendResult(accepted=True, provider="mock", message_id=msg_id)


class EmailService:
    """Dispatches transactional emails with support for multiple providers."""

    def __init__(self):
        self.provider = settings.EMAIL_PROVIDER.lower()

    @staticmethod
    def _build_mime(to_email: str, content: EmailContent) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = content.subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg["To"] = to_email
        msg.set_content(content.text_body)
        if content.html_body:
            msg.add_alternative(content.html_body, subtype="html")
        return msg

    async def _send_smtp(self, to_email: str, content: EmailContent) -> SendResult:
        msg = self._build_mime(to_email, content)
        host = settings.EMAIL_HOST
        port = settings.EMAIL_PORT
        use_tls = settings.EMAIL_USE_TLS
        username = settings.EMAIL_USERNAME
        password = settings.EMAIL_PASSWORD
        timeout = settings.EMAIL_TIMEOUT

        def _blocking_send():
            if use_tls and port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=timeout) as server:
                    if use_tls:
                        server.starttls()
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg)

        try:
            await asyncio.to_thread(_blocking_send)
            return SendResult(accepted=True, provider="smtp")
        except Exception as e:
            logger.error(f"SMTP dispatch failed to {to_email}: {e}")
            return SendResult(accepted=False, provider="smtp", error=str(e))

    async def send_email(self, to_email: str, content: EmailContent) -> SendResult:
        if self.provider in ("mock", "test"):
            return await MockEmailProvider.send(to_email, content)

        elif self.provider == "console":
            logger.info(f"=== CONSOLE EMAIL ===\nTo: {to_email}\nSubject: {content.subject}\nBody: {content.text_body}\n=====================")
            return SendResult(accepted=True, provider="console", message_id="console-1")

        elif self.provider == "smtp":
            # Retry up to 2 times for transient network failures
            delay = 0.5
            last_res = None
            for attempt in range(3):
                last_res = await self._send_smtp(to_email, content)
                if last_res.accepted:
                    return last_res
                if attempt < 2:
                    await asyncio.sleep(delay)
                    delay *= 2
            return last_res or SendResult(accepted=False, provider="smtp", error="Max retries exceeded")

        else:
            return SendResult(accepted=False, provider=self.provider, error=f"Unsupported email provider: {self.provider}")

    async def send_registration_otp(self, to_email: str, otp: str) -> SendResult:
        app_name = settings.APP_NAME
        safe_otp = html.escape(otp)
        subject = f"{app_name}: Account Registration Verification Code"
        text_body = (
            f"Welcome to {app_name}!\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.\n"
            f"If you did not request this, please contact your system administrator."
        )
        html_body = (
            f"<html><body style='font-family: Arial, sans-serif;'>"
            f"<h2>{app_name} Institutional AI Platform</h2>"
            f"<p>Welcome! Use the verification code below to complete your account registration:</p>"
            f"<h1 style='color: #1a73e8; letter-spacing: 4px;'>{safe_otp}</h1>"
            f"<p>This code will expire in <strong>{settings.OTP_EXPIRY_MINUTES} minutes</strong>.</p>"
            f"<p style='color: #666;'>If you did not request this registration, please contact your administrator.</p>"
            f"</body></html>"
        )
        return await self.send_email(to_email, EmailContent(subject=subject, text_body=text_body, html_body=html_body))

    async def send_login_mfa_otp(self, to_email: str, otp: str) -> SendResult:
        app_name = settings.APP_NAME
        safe_otp = html.escape(otp)
        subject = f"{app_name}: Login Verification Code"
        text_body = (
            f"{app_name} Security Verification\n\n"
            f"Your sign-in verification code is: {otp}\n\n"
            f"This code expires in {settings.MFA_EXPIRY_MINUTES} minutes.\n"
            f"If you did not attempt to log in, your account may be compromised. Alert an administrator immediately."
        )
        html_body = (
            f"<html><body style='font-family: Arial, sans-serif;'>"
            f"<h2>{app_name} Security Verification</h2>"
            f"<p>Use the code below to complete your sign-in:</p>"
            f"<h1 style='color: #d93025; letter-spacing: 4px;'>{safe_otp}</h1>"
            f"<p>This code expires in <strong>{settings.MFA_EXPIRY_MINUTES} minutes</strong>.</p>"
            f"<p style='color: #666;'>If you did not attempt to sign in, alert your administrator immediately.</p>"
            f"</body></html>"
        )
        return await self.send_email(to_email, EmailContent(subject=subject, text_body=text_body, html_body=html_body))
