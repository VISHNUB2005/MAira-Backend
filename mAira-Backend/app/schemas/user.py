"""User profile and account schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserProfileResponse(BaseModel):
    user_id: int
    email: EmailStr
    user_type: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserPasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
