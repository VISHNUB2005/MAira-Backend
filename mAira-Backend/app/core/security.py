"""Security, Cryptography, Bcrypt Hashing, and Token Management."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# ==============================================================================
# 1. BCRYPT PASSWORD HASHING WITH TIMING ATTACK MITIGATION
# ==============================================================================

# Precomputed constant hash for dummy verification to prevent timing side-channels
DUMMY_HASH = bcrypt.hashpw(b"timing_attack_mitigation_dummy_hash_secret", bcrypt.gensalt(12)).decode("utf-8")


def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt with cost factor 12."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify password against bcrypt hash safely.
    
    Executes a dummy bcrypt comparison if hashed_password is None or empty,
    guaranteeing uniform execution timing to thwart account enumeration.
    """
    if not plain_password or not hashed_password:
        bcrypt.checkpw(b"dummy_plain", DUMMY_HASH.encode("utf-8"))
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ==============================================================================
# 2. OTP GENERATION & CONSTANT-TIME VERIFICATION
# ==============================================================================

def generate_secure_otp(digits: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP."""
    min_val = 10 ** (digits - 1)
    max_val = (10 ** digits) - 1
    return str(secrets.randbelow(max_val - min_val + 1) + min_val)


def hash_otp(otp: str, email_salt: str = "") -> str:
    """Hash an OTP code with SHA-256 and email salt before database persistence."""
    data = f"{otp}:{email_salt.lower().strip()}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def verify_otp_hash(otp: str, stored_hash: str, email_salt: str = "") -> bool:
    """Constant-time verification of OTP code against stored SHA-256 hash."""
    if not otp or not stored_hash:
        return False
    calculated_hash = hash_otp(otp, email_salt)
    return secrets.compare_digest(calculated_hash, stored_hash)


# ==============================================================================
# 3. REFRESH TOKEN LIFECYCLE
# ==============================================================================

def create_refresh_token() -> str:
    """Generate cryptographically secure opaque 64-byte URL-safe refresh token."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    """Hash a refresh token using SHA-256 before storage."""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def verify_refresh_token(refresh_token: str, stored_hash: str) -> bool:
    """Verify refresh token in constant time."""
    if not refresh_token or not stored_hash:
        return False
    token_hash = hash_refresh_token(refresh_token)
    return secrets.compare_digest(token_hash, stored_hash)


# ==============================================================================
# 4. JWT ACCESS TOKEN MANAGEMENT
# ==============================================================================

def create_access_token(
    user_id: int | str,
    session_id: str,
    email: Optional[str] = None,
    role: Optional[str] = None,
    account_type: str = "USER",
    expires_minutes: Optional[int] = None,
) -> str:
    """Generate signed JWT access token adhering to the agreed Phase 1 contract."""
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
        "account_type": account_type.upper(),
    }
    if email:
        payload["email"] = email
    if role:
        payload["role"] = role

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and strictly validate JWT access token signature, expiry, and claims."""
    if not token:
        return None
    try:
        # Strictly enforce HS256 algorithm and reject none/tampered
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        if payload.get("type") != "access":
            return None
        if not all(k in payload for k in ("sub", "sid", "jti", "exp", "account_type")):
            return None
        return payload
    except JWTError:
        return None


# ==============================================================================
# 5. REGISTRATION VERIFICATION TICKET
# ==============================================================================

def create_registration_ticket(email: str, user_id: int, otp_id: str) -> str:
    """Create short-lived signed registration ticket bound to verified OTP record."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email.lower().strip(),
        "otp_id": str(otp_id),
        "type": "registration_verified",
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.REGISTRATION_TICKET_EXPIRE_MINUTES)).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_registration_ticket(ticket: str) -> Optional[Dict[str, Any]]:
    """Verify and decode registration ticket."""
    if not ticket:
        return None
    try:
        payload = jwt.decode(
            ticket,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        if payload.get("type") != "registration_verified":
            return None
        if not all(k in payload for k in ("sub", "email", "otp_id", "exp")):
            return None
        return payload
    except JWTError:
        return None


# ==============================================================================
# 6. MFA CHALLENGE TOKEN
# ==============================================================================

def create_mfa_challenge_token(
    account_id: int,
    email: str,
    role: str,
    account_type: str,
    otp_id: str,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create short-lived signed token representing pending MFA challenge."""
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or settings.MFA_EXPIRY_MINUTES
    payload = {
        "sub": str(account_id),
        "email": email.lower().strip(),
        "role": role,
        "account_type": account_type.upper(),
        "otp_id": str(otp_id),
        "type": "mfa_pending",
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_mfa_challenge_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate MFA challenge token."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        if payload.get("type") != "mfa_pending":
            return None
        if not all(k in payload for k in ("sub", "email", "role", "account_type", "otp_id", "exp")):
            return None
        return payload
    except JWTError:
        return None
