"""Application Exceptions and Global Exception Handlers."""

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.redaction import redact_sensitive_dict

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
    def __init__(self, message: str = "Invalid credentials", code: str = "AUTH_FAILED"):
        super().__init__(message, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """Raised when user lacks required role or permission."""
    def __init__(self, message: str = "Access denied", code: str = "FORBIDDEN"):
        super().__init__(message, code=code, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(message, code=code, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Raised when resource state conflicts with request."""
    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(message, code=code, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    """Raised when business validation fails."""
    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR"):
        super().__init__(message, code=code, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class AccountStatusError(AppException):
    """Raised when account is inactive or locked."""
    def __init__(self, message: str, code: str = "ACCOUNT_DISABLED"):
        super().__init__(message, code=code, status_code=status.HTTP_403_FORBIDDEN)


class OTPError(AppException):
    """Raised on OTP failure (expired, invalid, max attempts)."""
    def __init__(self, message: str, code: str = "OTP_INVALID"):
        super().__init__(message, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED", status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class GenAIServiceError(AppException):
    """Raised when Gen AI inference microservice is unavailable or errors."""
    def __init__(self, message: str = "AI service temporarily unavailable", code: str = "AI_SERVICE_UNAVAILABLE"):
        super().__init__(message, code=code, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register safe global exception handlers on FastAPI instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            f"AppException: code={exc.code} status={exc.status_code} "
            f"msg='{exc.message}' path='{request.url.path}' req_id={request_id}"
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
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        sanitized_errors = redact_sensitive_dict(exc.errors())
        logger.info(f"Request validation failure on {request.url.path}: {sanitized_errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Invalid request parameters or payload.",
                "details": sanitized_errors,
                "request_id": request_id,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", None)
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
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
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        # Log full traceback internally with sensitive fields redacted
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path} [req_id={request_id}]: {exc}",
            exc_info=True,
        )
        # Return generic safe response without exposing stack traces, hostnames, or DB errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact system support.",
                "request_id": request_id,
            },
        )
