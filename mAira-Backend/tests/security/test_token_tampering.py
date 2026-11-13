"""Security tests for JWT tampering and algorithm downgrade attacks."""

import base64
import json
import pytest
from httpx import AsyncClient
import jwt
from app.core.config import get_settings

settings = get_settings()


def b64url(data: dict) -> str:
    s = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(s).rstrip(b"=").decode("utf-8")


@pytest.mark.asyncio
async def test_none_algorithm_attack_rejected(client: AsyncClient):
    """Verify that manually crafted alg=none tokens are strictly rejected."""
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "sub": "1",
        "sid": "00000000-0000-0000-0000-000000000001",
        "jti": "rogue-jti",
        "iat": 1700000000,
        "exp": 1800000000,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
        "role": "ADMIN",
    }
    # Manually craft token with alg=none and empty signature
    rogue_token = f"{b64url(header)}.{b64url(payload)}."

    res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {rogue_token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_wrong_secret_key_rejected(client: AsyncClient):
    payload = {
        "sub": "1",
        "sid": "00000000-0000-0000-0000-000000000001",
        "jti": "jti-123",
        "iat": 1700000000,
        "exp": 1800000000,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
        "role": "STUDENT",
    }
    alien_token = jwt.encode(payload, key="completely_wrong_secret_key_32bytes_min!", algorithm="HS256")
    res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {alien_token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_wrong_audience_or_issuer_rejected(client: AsyncClient):
    payload = {
        "sub": "1",
        "sid": "00000000-0000-0000-0000-000000000001",
        "jti": "jti-123",
        "iat": 1700000000,
        "exp": 1800000000,
        "iss": "rogue-issuer",
        "aud": "rogue-audience",
        "type": "access",
        "role": "STUDENT",
    }
    bad_iss_token = jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm="HS256")
    res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {bad_iss_token}"})
    assert res.status_code == 401
