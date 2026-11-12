"""Centralized Secrets Management Provider.

Supports:
- Environment variables
- Docker / Kubernetes secrets (/run/secrets/<secret_name>)
- File-based secret references (<SECRET_NAME>_FILE)
- Secure masking of sensitive values for logging
"""

import os
from pathlib import Path
from typing import Optional


class MissingSecretError(RuntimeError):
    """Raised when a mandatory secret is not configured."""
    pass


DOCKER_SECRETS_DIR = Path("/run/secrets")


def read_file_secret(secret_name: str) -> Optional[str]:
    """Attempt to read secret from Docker secrets dir or *_FILE environment pointer."""
    # 1. Check Docker secrets mount
    if DOCKER_SECRETS_DIR.is_dir():
        secret_file = DOCKER_SECRETS_DIR / secret_name.lower()
        if secret_file.is_file():
            try:
                return secret_file.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug("Failed reading secret file %s: %s", secret_file, e)

    # 2. Check explicit *_FILE env var (e.g. JWT_SECRET_KEY_FILE)
    env_file_path = os.getenv(f"{secret_name.upper()}_FILE")
    if env_file_path and os.path.isfile(env_file_path):
        try:
            return Path(env_file_path).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as e:
            logger.debug("Failed reading secret from %s: %s", env_file_path, e)

    return None


def get_secret(secret_name: str, default: Optional[str] = None, required: bool = True) -> str:
    """Retrieve secret with fallback precedence: Env Var -> Docker/File -> Default."""
    val = os.getenv(secret_name)
    if val is None or val == "":
        val = read_file_secret(secret_name)
        if val is None or val == "":
            val = default

    if required and (val is None or val == ""):
        raise MissingSecretError(f"Required secret '{secret_name}' is not configured.")

    # Validation against obvious placeholder values
    if secret_name.upper() == "JWT_SECRET_KEY" and val:
        val_lower = val.lower()
        if any(placeholder in val_lower for placeholder in ["placeholder", "change-me", "your-secret", "example"]):
            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                raise ValueError("JWT_SECRET_KEY cannot use placeholder value in production.")
        if len(val.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes (256 bits).")

    return val or ""


def mask_secret(value: Optional[str], visible_chars: int = 2) -> str:
    """Mask a secret string for safe display in non-sensitive logs."""
    if not value:
        return "<empty>"
    length = len(value)
    if length <= visible_chars * 2:
        return "*" * length
    middle = "*" * max(8, length - (visible_chars * 2))
    return f"{value[:visible_chars]}{middle}{value[-visible_chars:]}"
