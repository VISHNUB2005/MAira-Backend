"""
xsc_lib_a_config.py
-------------------
Central, typed application settings. Every other module does:

    from xsc_lib.xsc_lib_app.xsc_lib_a_config import settings

Non-secret values come from environment variables with safe defaults.
Secrets are always read through xsc_lib_a_secrets.get_secret().
Config is validated when this module is first imported, so a missing JWT key,
SMTP host, sender or credential stops the app immediately instead of failing
on the first login. There are NO default credentials and NO default JWT key.

Supported EMAIL_PROVIDER values in this phase:
  smtp                       real delivery (needs host, sender, username, password)
  mock                       tests only (in-memory outbox)
  console, file              local development only (they print/save the OTP)
Amazon SES and SendGrid are NOT supported yet and are rejected explicitly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from xsc_lib.xsc_lib_app.xsc_lib_a_secrets import get_secret, secret_status

ENVIRONMENTS = {"development", "test", "staging", "production"}
DEV_ONLY_PROVIDERS = {"console", "file", "mock"}
SUPPORTED_PROVIDERS = {"smtp"} | DEV_ONLY_PROVIDERS
UNSUPPORTED_PROVIDERS = {"ses", "sendgrid"}
TLS_MODES = {"starttls", "ssl", "none"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _get_bool(name: str, default: bool = False) -> bool:
    return str(get_secret(name, str(default))).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = get_secret(name, str(default))
    try:
        return int(str(raw).strip())
    except ValueError:
        # Do not echo the value back.
        raise RuntimeError(f"{name} must be a whole number") from None


def _get_list(name: str, default: str = "") -> List[str]:
    raw = get_secret(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def _first_value(*names: str, default: str = "") -> str:
    """First name that has a non-blank value (EMAIL_* names first, SMTP_* as fallback)."""
    for name in names:
        value = get_secret(name)
        if value:
            return value.strip()
    return default


def _first_int(*names: str, default: int) -> int:
    for name in names:
        if get_secret(name):
            return _get_int(name, default)
    return default


def _clean_password(*names: str) -> str:
    """First non-blank value among `names`, with ALL whitespace removed.
    Google shows app passwords in groups ("abcd efgh ijkl mnop") but they contain no spaces."""
    for name in names:
        value = get_secret(name)
        if value:
            return "".join(value.split())
    return ""


def _status(*names: str) -> str:
    """'set' / 'empty' / 'unset' for the first name that is defined at all."""
    for name in names:
        state = secret_status(name)
        if state != "unset":
            return state
    return "unset"


# ---------------------------------------------------------------------------
# Email address validation (shared by this module and the email service)
# ---------------------------------------------------------------------------
_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_LABEL_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


def _strict_validate(address: str) -> str:
    """Built-in fallback validator (ASCII only). Used when `email-validator` is not installed."""
    address = address.strip()
    if len(address) > 254 or address.count("@") != 1:
        raise ValueError("invalid email address")
    local, domain = address.split("@")
    if (
        not 1 <= len(local) <= 64
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or not _LOCAL_RE.match(local)
    ):
        raise ValueError("invalid email address")
    labels = domain.lower().split(".")
    if len(labels) < 2 or not all(_LABEL_RE.match(label) for label in labels) or labels[-1].isdigit():
        raise ValueError("invalid email address")
    return f"{local}@{domain.lower()}"


def validate_email_address(address: Optional[str]) -> str:
    """Return the normalized address or raise ValueError("invalid email address").

    Uses the maintained `email-validator` package when installed (syntax only, no DNS lookups),
    otherwise a strict built-in check. The message never contains the address.
    """
    if not isinstance(address, str) or not address.strip():
        raise ValueError("invalid email address")
    if any(ch in address for ch in "\r\n\x00"):
        raise ValueError("invalid email address")
    try:
        import email_validator
    except ImportError:
        return _strict_validate(address)
    try:
        info = email_validator.validate_email(address.strip(), check_deliverability=False)
    except email_validator.EmailNotValidError:
        raise ValueError("invalid email address") from None
    return getattr(info, "normalized", None) or info.email


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    # ---- General ---------------------------------------------------------
    app_name: str = field(default_factory=lambda: get_secret("APP_NAME", "MAira"))
    environment: str = field(default_factory=lambda: get_secret("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: _get_bool("DEBUG", False))
    cors_origins: List[str] = field(
        default_factory=lambda: _get_list("CORS_ORIGINS", "http://localhost:3000")
    )

    # ---- Database --------------------------------------------------------
    database_url: str = field(
        default_factory=lambda: get_secret("DATABASE_URL", required=True), repr=False
    )

    # ---- Auth / JWT (no default key: it must be provided) ------------------
    jwt_secret_key: str = field(
        default_factory=lambda: get_secret("JWT_SECRET_KEY", required=True), repr=False
    )
    jwt_algorithm: str = field(default_factory=lambda: get_secret("JWT_ALGORITHM", "HS256"))
    access_token_minutes: int = field(default_factory=lambda: _get_int("ACCESS_TOKEN_MINUTES", 15))
    refresh_token_days: int = field(default_factory=lambda: _get_int("REFRESH_TOKEN_DAYS", 7))

    # ---- OTP (generation/verification belong to Group 3) -----------------
    otp_length: int = field(default_factory=lambda: _get_int("OTP_LENGTH", 6))
    otp_expiry_minutes: int = field(default_factory=lambda: _get_int("OTP_EXPIRY_MINUTES", 5))
    otp_max_attempts: int = field(default_factory=lambda: _get_int("OTP_MAX_ATTEMPTS", 5))

    # ---- Registration (the domain policy itself is enforced by Group 1) ----
    allowed_email_domains: List[str] = field(
        default_factory=lambda: _get_list("ALLOWED_EMAIL_DOMAINS", "organization.com")
    )

    # ---- Email -----------------------------------------------------------
    # EMAIL_PROVIDER: smtp | mock | console | file   (console/file/mock: development and test only)
    email_provider: str = field(default_factory=lambda: get_secret("EMAIL_PROVIDER", "console"))
    email_from_address: str = field(default_factory=lambda: get_secret("EMAIL_FROM_ADDRESS", "").strip())
    email_from_name: str = field(default_factory=lambda: get_secret("EMAIL_FROM_NAME", "MAira"))
    email_outbox_dir: str = field(default_factory=lambda: get_secret("EMAIL_OUTBOX_DIR", "outbox"))

    # SMTP. Preferred names: EMAIL_HOST / EMAIL_PORT / EMAIL_USERNAME / EMAIL_PASSWORD.
    # The older SMTP_* names still work as a fallback. No host/credential defaults.
    smtp_host: str = field(default_factory=lambda: _first_value("EMAIL_HOST", "SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: _first_int("EMAIL_PORT", "SMTP_PORT", default=587))
    smtp_username: str = field(
        default_factory=lambda: _first_value("EMAIL_USERNAME", "SMTP_USERNAME"), repr=False
    )
    smtp_password: str = field(
        default_factory=lambda: _clean_password("EMAIL_PASSWORD", "SMTP_PASSWORD"), repr=False
    )
    # EMAIL_TLS_MODE: starttls (port 587, default) | ssl (port 465) | none (development/test only)
    email_tls_mode: str = field(
        default_factory=lambda: get_secret("EMAIL_TLS_MODE", "starttls").strip().lower()
    )
    email_timeout_seconds: int = field(default_factory=lambda: _get_int("EMAIL_TIMEOUT_SECONDS", 15))

    # ------------------------------------------------------------------
    def _need(self, problems: List[str], label: str, *names: str) -> None:
        state = _status(*names)
        if state == "unset":
            problems.append(f"{label} is not set")
        elif state == "empty":
            problems.append(f"{label} is set but empty")

    def validate(self) -> None:
        """Fail fast on unsafe or incomplete configuration. Messages never contain secret values."""
        problems: List[str] = []

        # ---- JWT --------------------------------------------------------
        if len(self.jwt_secret_key) < 32:
            problems.append("JWT_SECRET_KEY must be at least 32 characters")
        if "change-me" in self.jwt_secret_key.lower():
            problems.append("JWT_SECRET_KEY is still the placeholder from .env.example")

        # ---- environment --------------------------------------------------
        if self.environment not in ENVIRONMENTS:
            problems.append(f"ENVIRONMENT must be one of: {', '.join(sorted(ENVIRONMENTS))}")
        if self.environment == "production":
            if self.debug:
                problems.append("DEBUG must be false in production")
            if "*" in self.cors_origins:
                problems.append("CORS_ORIGINS must not contain '*' in production")

        # ---- numbers --------------------------------------------------------
        if not 4 <= self.otp_length <= 10:
            problems.append("OTP_LENGTH must be between 4 and 10")
        if self.otp_expiry_minutes < 1:
            problems.append("OTP_EXPIRY_MINUTES must be at least 1")
        if self.otp_max_attempts < 1:
            problems.append("OTP_MAX_ATTEMPTS must be at least 1")
        if self.access_token_minutes < 1 or self.refresh_token_days < 1:
            problems.append("ACCESS_TOKEN_MINUTES and REFRESH_TOKEN_DAYS must be at least 1")

        # ---- provider -------------------------------------------------------
        provider = self.email_provider
        if provider in UNSUPPORTED_PROVIDERS:
            problems.append(
                f"EMAIL_PROVIDER={provider} is not supported in this phase "
                "(use smtp; console/file/mock for development and tests)"
            )
        elif provider not in SUPPORTED_PROVIDERS:
            problems.append(f"Unknown EMAIL_PROVIDER '{provider}'")
        if provider in DEV_ONLY_PROVIDERS and self.environment not in {"development", "test"}:
            problems.append(
                f"EMAIL_PROVIDER={provider} is only allowed when ENVIRONMENT is development or test "
                "(console/file print or save OTPs)"
            )

        # ---- SMTP ---------------------------------------------------------
        if provider == "smtp":
            self._need(problems, "EMAIL_HOST", "EMAIL_HOST", "SMTP_HOST")
            self._need(problems, "EMAIL_USERNAME", "EMAIL_USERNAME", "SMTP_USERNAME")
            self._need(problems, "EMAIL_PASSWORD", "EMAIL_PASSWORD", "SMTP_PASSWORD")

            sender_state = _status("EMAIL_FROM_ADDRESS")
            if sender_state == "unset":
                problems.append("EMAIL_FROM_ADDRESS is not set")
            elif sender_state == "empty":
                problems.append("EMAIL_FROM_ADDRESS is set but empty")
            else:
                try:
                    validate_email_address(self.email_from_address)
                except ValueError:
                    problems.append("EMAIL_FROM_ADDRESS is not a valid email address")

            if not 1 <= self.smtp_port <= 65535:
                problems.append("EMAIL_PORT must be between 1 and 65535")
            if not 1 <= self.email_timeout_seconds <= 120:
                problems.append("EMAIL_TIMEOUT_SECONDS must be between 1 and 120")
            if self.email_tls_mode not in TLS_MODES:
                problems.append("EMAIL_TLS_MODE must be starttls, ssl or none")
            elif self.email_tls_mode == "none" and self.environment not in {"development", "test"}:
                problems.append("EMAIL_TLS_MODE=none is only allowed in development or test")

        if problems:
            raise RuntimeError("Invalid configuration:\n - " + "\n - ".join(problems))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.validate()
    return s


settings = get_settings()
