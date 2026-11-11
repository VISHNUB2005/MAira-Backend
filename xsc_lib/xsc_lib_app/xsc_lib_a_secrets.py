"""
xsc_lib_a_secrets.py
--------------------
Single place where secrets are read. Nothing else in the project should call
os.getenv() for passwords, keys or tokens.

Lookup order (first non-blank hit wins):
  1. Environment variable NAME          (.env file in dev, real env vars in prod)
  2. File named by NAME_FILE            (e.g. JWT_SECRET_KEY_FILE=/run/secrets/jwt)
  3. Docker/Kubernetes secret file      (/run/secrets/<name_lowercase>)
  4. AWS Secrets Manager                (only if AWS_SECRETS_NAME is set)

Failure behaviour (never includes secret values):
  - NAME_FILE set but the file does not exist       -> SecretFileError
  - a secret file exists but cannot be read         -> SecretFileError
  - an empty / whitespace-only value                -> treated as "not provided"
  - required secret not provided anywhere           -> MissingSecretError

Requires: python-dotenv  (boto3 only if you use AWS Secrets Manager)
"""
from __future__ import annotations

import json
import logging
import os
import secrets as _stdlib_secrets
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Optional

from dotenv import load_dotenv

# Load .env into os.environ once, at import time. Real env vars win over .env.
load_dotenv(override=False)

logger = logging.getLogger(__name__)

DOCKER_SECRETS_DIR = Path(os.getenv("SECRETS_DIR", "/run/secrets"))


class MissingSecretError(RuntimeError):
    """Raised when a required secret cannot be found in any source."""


class SecretFileError(RuntimeError):
    """Raised when a secret file is missing (NAME_FILE) or cannot be read."""


@lru_cache(maxsize=1)
def _load_aws_secret_bundle() -> dict:
    """Fetch one JSON secret from AWS Secrets Manager (cached for the process)."""
    secret_name = os.getenv("AWS_SECRETS_NAME")
    if not secret_name:
        return {}
    try:
        import boto3  # imported lazily so boto3 is optional

        client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION"))
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception:  # never leak details of the secret store
        logger.error("Could not load secrets from AWS Secrets Manager")
        return {}


def _read_file(path: Path, name: str) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        # Do not echo the OS error text; it can contain paths and details.
        raise SecretFileError(f"Secret file for '{name}' exists but cannot be read") from None


def _sources(name: str) -> Iterator[str]:
    """Yield the raw value from each source that defines `name`, in precedence order."""
    raw = os.getenv(name)
    if raw is not None:
        yield raw

    file_var = os.getenv(f"{name}_FILE")
    if file_var:
        path = Path(file_var)
        if not path.is_file():
            raise SecretFileError(f"{name}_FILE points to a file that does not exist")
        yield _read_file(path, name)

    docker_file = DOCKER_SECRETS_DIR / name.lower()
    if docker_file.is_file():
        yield _read_file(docker_file, name)

    aws_value = _load_aws_secret_bundle().get(name)
    if aws_value is not None:
        yield str(aws_value)


def get_secret(
    name: str, default: Optional[str] = None, required: bool = False
) -> Optional[str]:
    """Return the secret called `name`, or `default`. Raises if `required` and missing."""
    value: Optional[str] = None
    for raw in _sources(name):
        if raw.strip():
            value = raw
            break

    if not value:
        value = default

    if required and not value:
        raise MissingSecretError(f"Required secret '{name}' is not set or is empty")
    return value


def secret_status(name: str) -> str:
    """'set', 'empty' (defined but blank) or 'unset'. Never reveals the value."""
    seen_blank = False
    for raw in _sources(name):
        if raw.strip():
            return "set"
        seen_blank = True
    return "empty" if seen_blank else "unset"


def mask_secret(value: Optional[str], visible: int = 2) -> str:
    """Safe-for-logs representation, e.g. 'ab********yz'."""
    if not value:
        return "<empty>"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * 8}{value[-visible:]}"


def generate_secret_key(nbytes: int = 64) -> str:
    """Generate a strong random key (use once, e.g. for JWT_SECRET_KEY)."""
    return _stdlib_secrets.token_urlsafe(nbytes)


if __name__ == "__main__":
    # python -m xsc_lib.xsc_lib_app.xsc_lib_a_secrets
    print("New JWT_SECRET_KEY:", generate_secret_key())
