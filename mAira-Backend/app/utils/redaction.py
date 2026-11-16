"""Sensitive data redaction utilities."""

import re
from typing import Any, Dict, List, Union

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "new_password",
    "old_password",
    "confirm_password",
    "secret",
    "jwt_secret_key",
    "otp",
    "otp_hash",
    "token",
    "access_token",
    "refresh_token",
    "refresh_token_hash",
    "authorization",
    "cookie",
    "set-cookie",
    "db_password",
    "email_password",
    "smtp_password",
    "service_secret",
}

EMAIL_REGEX = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")


def mask_email(email: str) -> str:
    """Mask email address for privacy (e.g. j***e@domain.com)."""
    if not email or "@" not in email:
        return email
    parts = email.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{masked_user}@{domain}"


def redact_sensitive_dict(data: Any) -> Any:
    """Recursively redact sensitive fields in dictionaries and lists."""
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                redacted[key] = redact_sensitive_dict(value)
            else:
                redacted[key] = value
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]
    return data
