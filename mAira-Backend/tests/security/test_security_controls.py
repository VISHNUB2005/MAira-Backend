"""Security tests for HTTP security headers, CORS, and request correlation."""

import pytest
from httpx import AsyncClient
from app.security.rate_limiter import InMemoryRateLimiter


@pytest.mark.asyncio
async def test_security_headers_present_on_endpoints(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "camera=()" in headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_request_correlation_id_generated_and_propagated(client: AsyncClient):
    # Auto-generation
    res1 = await client.get("/health")
    assert "X-Request-ID" in res1.headers
    assert len(res1.headers["X-Request-ID"]) > 10

    # Pass-through custom correlation ID
    custom_id = "institutional-correlation-998877"
    res2 = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert res2.headers.get("X-Request-ID") == custom_id


def test_rate_limiter_blocks_abuse():
    limiter = InMemoryRateLimiter()
    key = "attacker-ip-127.0.0.1"

    # Allow 3 requests in 60s
    assert limiter.is_allowed(key, max_requests=3, window_seconds=60)[0] is True
    assert limiter.is_allowed(key, max_requests=3, window_seconds=60)[0] is True
    assert limiter.is_allowed(key, max_requests=3, window_seconds=60)[0] is True

    # 4th request must be rejected
    allowed, retry_after = limiter.is_allowed(key, max_requests=3, window_seconds=60)
    assert allowed is False
    assert retry_after > 0
