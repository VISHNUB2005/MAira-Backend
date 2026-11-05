
import os
import jwt
import secrets
import hashlib

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()


def get_jwt_secret_key() -> str:
    """Return the configured JWT secret after validating its strength."""
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    if len(JWT_SECRET_KEY.encode("utf-8")) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must contain at least 32 bytes."
        )

    return JWT_SECRET_KEY


# JWT configuration
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "maira-backend")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "maira-api")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

# TEMPORARY IN-MEMORY STORAGE
# Replace with database persistence when the database team provides its code.
_REFRESH_SESSIONS = {}
_REVOKED_SESSIONS = set()


def create_access_token(
    user_id: str,
    session_id: str,
    secret_key: str,
    email: str = None,
    role: str = None,
    expires_minutes: int = None
):
    """Generate a signed JWT access token."""

    if not user_id or not session_id or not secret_key:
        raise ValueError("User ID, session ID and secret key are required.")

    now = datetime.now(timezone.utc)
    expiry = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES

    if expiry <= 0:
        raise ValueError("Token expiry must be positive.")

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=expiry),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "access"
    }

    if email:
        payload["email"] = email

    if role:
        payload["role"] = role

    return jwt.encode(
        payload,
        secret_key,
        algorithm=JWT_ALGORITHM
    )


def verify_access_token(token: str, secret_key: str):
    """Verify access token signature, expiry and claims."""

    if not token or not secret_key:
        return None

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE
        )

        if payload.get("type") != "access":
            return None

        if not all(payload.get(key) for key in ("sub", "sid", "jti")):
            return None

        if payload["sid"] in _REVOKED_SESSIONS:
            return None

        return payload

    except jwt.InvalidTokenError:
        return None


def create_refresh_token():
    """Generate a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str):
    """Hash a refresh token before storage."""
    return hashlib.sha256(
        refresh_token.encode("utf-8")
    ).hexdigest()


def verify_refresh_token(refresh_token: str, stored_hash: str):
    """Compare refresh token with its stored hash."""

    if not refresh_token or not stored_hash:
        return False

    token_hash = hash_refresh_token(refresh_token)

    return secrets.compare_digest(token_hash, stored_hash)


def register_refresh_token(
    refresh_token: str,
    user_id: str,
    session_id: str,
    email: str = None,
    role: str = None,
    expires_days: int = None
):
    """Register a refresh token in temporary memory.

    DATABASE PENDING:
    Store the token hash, user ID, session ID and expiry
    in the database when database-team code is available.
    """

    if not refresh_token or not user_id or not session_id:
        raise ValueError("Refresh token, user ID and session ID are required.")

    expiry_days = expires_days or REFRESH_TOKEN_EXPIRE_DAYS

    if expiry_days <= 0:
        raise ValueError("Refresh token expiry must be positive.")

    token_hash = hash_refresh_token(refresh_token)

    _REFRESH_SESSIONS[token_hash] = {
        "user_id": str(user_id),
        "session_id": str(session_id),
        "email": email,
        "role": role,
        "expires_at": datetime.now(timezone.utc)
        + timedelta(days=expiry_days),
        "revoked": False
    }

    return True


def create_session_tokens(
    user_id: str,
    session_id: str,
    secret_key: str,
    email: str = None,
    role: str = None
):
    """Create an access token and registered refresh token."""

    if session_id in _REVOKED_SESSIONS:
        raise ValueError("Session has been revoked.")

    access_token = create_access_token(
        user_id, session_id, secret_key, email, role
    )

    refresh_token = create_refresh_token()

    register_refresh_token(
        refresh_token, user_id, session_id, email, role
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_session(refresh_token: str, secret_key: str):
    """Validate, rotate and issue a new token pair."""

    if not refresh_token or not secret_key:
        return None

    token_hash = hash_refresh_token(refresh_token)
    record = _REFRESH_SESSIONS.get(token_hash)

    if not record:
        return None

    if record["revoked"]:
        return None

    if datetime.now(timezone.utc) >= record["expires_at"]:
        _REFRESH_SESSIONS.pop(token_hash, None)
        return None

    session_id = record["session_id"]

    if session_id in _REVOKED_SESSIONS:
        return None

    # Rotate old refresh token to prevent reuse.
    record["revoked"] = True

    return create_session_tokens(
        user_id=record["user_id"],
        session_id=session_id,
        secret_key=secret_key,
        email=record["email"],
        role=record["role"]
    )


def revoke_refresh_token(refresh_token: str):
    """Revoke one refresh token."""

    if not refresh_token:
        return False

    token_hash = hash_refresh_token(refresh_token)
    record = _REFRESH_SESSIONS.get(token_hash)

    if not record or record["revoked"]:
        return False

    record["revoked"] = True
    return True


def revoke_session(session_id: str):
    """Revoke a session and all its refresh tokens."""

    if not session_id:
        return False

    _REVOKED_SESSIONS.add(str(session_id))

    for record in _REFRESH_SESSIONS.values():
        if record["session_id"] == str(session_id):
            record["revoked"] = True

    return True


def logout(session_id: str):
    """Log out by revoking the session."""

    return revoke_session(session_id)


