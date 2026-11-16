
"""Application Exceptions and Global Exception Handlers."""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("maira.exceptions")


class AppException(Exception):
    """Base class for all application-level domain exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        code: str = "AUTH_FAILED",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppException):
    """Raised when user lacks required role or permission."""

    def __init__(
        self,
        message: str = "Access denied",
        code: str = "FORBIDDEN",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppException):
    """Raised when resource state conflicts with request."""

    def __init__(
        self,
        message: str = "Resource conflict",
        code: str = "CONFLICT",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
        )


class ValidationError(AppException):
    """Raised when business validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class AccountStatusError(AppException):
    """Raised when account is inactive or locked."""

    def __init__(
        self,
        message: str,
        code: str = "ACCOUNT_DISABLED",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class OTPError(AppException):
    """Raised on OTP failure (expired, invalid, max attempts)."""

    def __init__(
        self,
        message: str,
        code: str = "OTP_INVALID",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
    ):
        super().__init__(
            message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class GenAIServiceError(AppException):
    """Raised when Gen AI inference microservice is unavailable or errors."""

    def __init__(
        self,
        message: str = "AI service temporarily unavailable",
        code: str = "AI_SERVICE_UNAVAILABLE",
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _safe_validation_errors(exc: RequestValidationError) -> list:
    """
    Extract only JSON-safe validation information.

    Deliberately excludes:
    - input: may contain passwords, OTPs, tokens or other submitted data.
    - ctx: may contain non-serializable Python exception objects.
    """

    safe_errors = []

    for error in exc.errors():
        location = error.get("loc", ())

        # Remove the generic "body", "query", etc. prefix from the field name.
        field_parts = [
            str(part)
            for part in location
            if part not in ("body", "query", "path", "header", "cookie")
        ]

        field = ".".join(field_parts) or "request"

        message = error.get("msg")
        if not isinstance(message, str):
            message = "Invalid value."

        error_type = error.get("type")
        if not isinstance(error_type, str):
            error_type = "validation_error"

        safe_errors.append(
            {
                "field": field[:200],
                "message": message[:300],
                "type": error_type[:100],
            }
        )

    return safe_errors


def setup_exception_handlers(app: FastAPI) -> None:
    """Register safe global exception handlers on the FastAPI instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", None)

        # Do not log exception messages; they may contain sensitive data.
        logger.warning(
            "AppException: code=%s status=%s path=%s request_id=%s",
            exc.code,
            exc.status_code,
            request.url.path,
            request_id,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        request_id = getattr(request.state, "request_id", None)

        safe_errors = _safe_validation_errors(exc)

        # Log field names and error types only.
        # Never log the request body, submitted values, or raw exc.errors().
        logger.warning(
            "Request validation failure: path=%s request_id=%s errors=%s",
            request.url.path,
            request_id,
            [
                {
                    "field": error["field"],
                    "type": error["type"],
                }
                for error in safe_errors
            ],
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Invalid request parameters or payload.",
                "details": safe_errors,
                "request_id": request_id,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ):
        request_id = getattr(request.state, "request_id", None)

        detail = (
            exc.detail
            if isinstance(exc.detail, str)
            else "HTTP error"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": f"HTTP_{exc.status_code}",
                "message": detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        request_id = getattr(request.state, "request_id", None)

        # Do not log exception text or request data because either may
        # contain credentials, tokens, database values or other secrets.
        logger.error(
            "Unhandled exception: method=%s path=%s exception_type=%s request_id=%s",
            request.method,
            request.url.path,
            type(exc).__name__,
            request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": (
                    "An unexpected error occurred. "
                    "Please contact system support."
                ),
                "request_id": request_id,
            },
        )
