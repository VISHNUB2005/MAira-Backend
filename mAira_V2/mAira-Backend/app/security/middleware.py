
"""Security Headers, Correlation ID, and Middleware Configuration."""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Binds unique request_id to request state and passes it through in responses."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces defense-in-depth secure HTTP headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # Documentation-specific CSP.
        # Keep external resource permissions limited to Swagger and ReDoc.
        docs_paths = {
            "/docs",
            "/redoc",
            "/docs/oauth2-redirect",
        }

        if request.url.path in docs_paths:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' "
                "https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: "
                "https://fastapi.tiangolo.com https://cdn.redoc.ly; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "connect-src 'self' https://cdn.jsdelivr.net; "
                "worker-src 'self' blob:; "
                "frame-ancestors 'none';"
            )
        else:
            # Strict CSP for all other application routes.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none';"
            )

        # HSTS only in production with debug disabled.
        if not settings.DEBUG and settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all application middleware."""

    # 1. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Security Headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. Request Correlation ID
    app.add_middleware(CorrelationIdMiddleware)
