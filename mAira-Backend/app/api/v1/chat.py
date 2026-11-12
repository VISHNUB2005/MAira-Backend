"""Chat and Conversation Management API Endpoints (Canonical /chat/sessions)."""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AuthenticatedAccount,
    get_current_account,
    get_db,
    require_permission,
)
from app.core.config import get_settings
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    MessageSend,
)
from app.schemas.common import MessageOnlyResponse
from app.security.permissions import (
    AI_USE,
    CHAT_CREATE,
    CHAT_DELETE_OWN,
    CHAT_VIEW_OWN,
)
from app.security.rate_limiter import rate_limiter
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat & Conversations"])
settings = get_settings()


# ==============================================================================
# Canonical Routes: /chat/sessions
# ==============================================================================

@router.post(
    "/sessions",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    summary="Legacy alias for creating session",
)
async def create_session(
    payload: ConversationCreate = ConversationCreate(),
    account: AuthenticatedAccount = Depends(require_permission(CHAT_CREATE)),
    session: AsyncSession = Depends(get_db),
):
    """Initialize a new chat conversation for the authenticated user."""
    chat_service = ChatService(session)
    return await chat_service.create_conversation(
        account_type=account.account_type,
        account_id=account.account_id,
        title=payload.title,
    )


@router.get(
    "/sessions",
    response_model=ConversationListResponse,
    summary="List chat sessions for authenticated user",
)
@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    include_in_schema=False,
    summary="Legacy alias for listing sessions",
)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account: AuthenticatedAccount = Depends(require_permission(CHAT_VIEW_OWN)),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve active conversations owned by the caller."""
    chat_service = ChatService(session)
    return await chat_service.list_conversations(
        account_type=account.account_type,
        account_id=account.account_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ConversationDetailResponse,
    summary="Get chat session details and message history",
)
@router.get(
    "/conversations/{session_id}",
    response_model=ConversationDetailResponse,
    include_in_schema=False,
    summary="Legacy alias for getting session details",
)
async def get_session(
    session_id: UUID,
    account: AuthenticatedAccount = Depends(require_permission(CHAT_VIEW_OWN)),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve message history for a conversation owned by the caller."""
    chat_service = ChatService(session)
    return await chat_service.get_conversation_detail(
        chat_session_id=session_id,
        account_type=account.account_type,
        account_id=account.account_id,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageOnlyResponse,
    summary="Soft-delete a chat session",
)
@router.delete(
    "/conversations/{session_id}",
    response_model=MessageOnlyResponse,
    include_in_schema=False,
    summary="Legacy alias for deleting session",
)
async def delete_session(
    session_id: UUID,
    account: AuthenticatedAccount = Depends(require_permission(CHAT_DELETE_OWN)),
    session: AsyncSession = Depends(get_db),
):
    """Soft delete a conversation owned by the caller."""
    chat_service = ChatService(session)
    await chat_service.soft_delete_conversation(
        chat_session_id=session_id,
        account_type=account.account_type,
        account_id=account.account_id,
    )
    return MessageOnlyResponse(message="Conversation deleted successfully.")


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    summary="Send message and receive AI-generated response",
)
@router.post(
    "/conversations/{session_id}/messages",
    response_model=MessageResponse,
    include_in_schema=False,
    summary="Legacy alias for sending message",
)
async def send_message(
    session_id: UUID,
    payload: MessageSend,
    request: Request,
    account: AuthenticatedAccount = Depends(require_permission(AI_USE)),
    session: AsyncSession = Depends(get_db),
):
    """Submit prompt, query local Gen AI microservice, and persist dialogue in PostgreSQL."""
    rate_limiter.check_rate_limit(
        key=f"chat:{account.account_id}",
        max_requests=settings.RATE_LIMIT_CHAT_MAX,
        window_seconds=settings.RATE_LIMIT_CHAT_WINDOW_SECONDS,
    )

    req_id = getattr(request.state, "request_id", None)
    chat_service = ChatService(session)
    user_msg, assistant_msg = await chat_service.send_message_and_get_response(
        chat_session_id=session_id,
        account_type=account.account_type,
        account_id=account.account_id,
        user_prompt=payload.content,
        request_id=req_id,
    )

    return MessageResponse(
        message_id=assistant_msg.message_id,
        chat_session_id=assistant_msg.chat_session_id,
        sender=assistant_msg.sender,
        content=assistant_msg.content,
        status=assistant_msg.status,
        model_name=assistant_msg.model_name,
        input_tokens=assistant_msg.input_tokens,
        output_tokens=assistant_msg.output_tokens,
        response_time_ms=assistant_msg.response_time_ms,
        created_at=assistant_msg.created_at,
    )
