"""Admin management schemas."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class StudentCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=150)
    user_type: Literal["STUDENT", "FACULTY"] = "STUDENT"


class StudentStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "INACTIVE"]


class StudentItem(BaseModel):
    user_id: int
    email: str
    user_type: str
    status: str
    password_set: bool
    created_at: datetime


class StudentListResponse(BaseModel):
    total: int
    students: List[StudentItem]


class StudentAnalyticsResponse(BaseModel):
    total_students: int
    active_students: int
    inactive_students: int
