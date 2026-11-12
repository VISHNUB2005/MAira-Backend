"""In-Memory Sliding Window Rate Limiter for Sensitive Endpoints.

NOTE: This is a single-process in-memory rate limiter. It provides rate limiting
within an individual process. In multi-worker or multi-instance deployments,
each worker enforces its own local sliding window. Distributed rate limiting
across multiple instances requires an external shared store (e.g. Redis), which
is documented as a pending architectural approval item.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError

settings = get_settings()


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter keyed by client identifier."""

    def __init__(self):
        # Maps key -> list of timestamp floats
        self._history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Check if request is allowed. Returns (is_allowed, retry_after_seconds)."""
        now = time.time()
        window_start = now - window_seconds

        # Prune timestamps older than current window
        timestamps = [t for t in self._history[key] if t > window_start]
        self._history[key] = timestamps

        if len(timestamps) >= max_requests:
            oldest = timestamps[0]
            retry_after = int(oldest + window_seconds - now) + 1
            return False, max(1, retry_after)

        self._history[key].append(now)
        return True, 0

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        allowed, retry_after = self.is_allowed(key, max_requests, window_seconds)
        if not allowed:
            raise RateLimitExceededError(
                f"Too many requests. Please try again in {retry_after} second(s)."
            )


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP safely without blindly trusting unauthenticated X-Forwarded-For headers.
    
    To prevent spoofing attacks that bypass rate limiting by injecting arbitrary
    headers, we prioritize the TCP socket peer address (`request.client.host`).
    """
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
