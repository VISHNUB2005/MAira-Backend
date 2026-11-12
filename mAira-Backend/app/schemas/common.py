"""Common API schemas."""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API envelope."""
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None
    request_id: Optional[str] = None


class MessageOnlyResponse(BaseModel):
    """Simple confirmation response."""
    status: str = "success"
    message: str
    request_id: Optional[str] = None
