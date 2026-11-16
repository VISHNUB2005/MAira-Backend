"""Chat and conversation schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    chat_session_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    total: int
    conversations: List[ConversationResponse]


class MessageSend(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    message_id: UUID
    chat_session_id: UUID
    sender: str  # USER, ASSISTANT
    content: str
    status: str  # PENDING, COMPLETED, FAILED
    model_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    response_time_ms: Optional[int] = None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
