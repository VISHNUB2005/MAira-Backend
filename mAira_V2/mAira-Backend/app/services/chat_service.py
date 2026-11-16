"""Chat and Conversation Management Service."""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.chat import ChatSession
from app.models.message import Message
from app.repositories.audit_repo import AuditRepository
from app.repositories.chat_repo import ChatRepository
from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.genai_service import GenAIClient, GenAIResult


class ChatService:
    """Orchestrates conversations, persistence, and AI inference requests."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.audit_repo = AuditRepository(session)
        self.genai_client = GenAIClient()

    # ================= Conversation Lifecycle =================
    async def create_conversation(
        self, account_type: str, account_id: int, title: Optional[str] = None
    ) -> ConversationResponse:
        chat = await self.chat_repo.create_chat_session(
            account_type=account_type,
            account_id=account_id,
            title=title or "New Conversation",
        )
        return ConversationResponse(
            chat_session_id=chat.chat_session_id,
            title=chat.title or "New Conversation",
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def list_conversations(
        self, account_type: str, account_id: int, limit: int = 50, offset: int = 0
    ) -> ConversationListResponse:
        chats = await self.chat_repo.list_chat_sessions(
            account_type=account_type,
            account_id=account_id,
            limit=limit,
            offset=offset,
            include_deleted=False,
        )
        items = [
            ConversationResponse(
                chat_session_id=c.chat_session_id,
                title=c.title or "Conversation",
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in chats
        ]
        return ConversationListResponse(total=len(items), conversations=items)

    async def get_conversation_detail(
        self, chat_session_id: UUID, account_type: str, account_id: int
    ) -> ConversationDetailResponse:
        chat = await self.chat_repo.get_chat_session(
            chat_session_id=chat_session_id,
            account_type=account_type,
            account_id=account_id,
            allow_deleted=False,
        )
        if not chat:
            raise NotFoundError("Conversation not found or access denied.")

        messages = await self.chat_repo.list_messages_for_chat(chat_session_id)
        msg_items = [
            MessageResponse(
                message_id=m.message_id,
                chat_session_id=m.chat_session_id,
                sender=m.sender,
                content=m.content,
                status=m.status,
                model_name=m.model_name,
                input_tokens=m.input_tokens,
                output_tokens=m.output_tokens,
                response_time_ms=m.response_time_ms,
                created_at=m.created_at,
            )
            for m in messages
        ]

        conv_item = ConversationResponse(
            chat_session_id=chat.chat_session_id,
            title=chat.title or "Conversation",
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
        return ConversationDetailResponse(conversation=conv_item, messages=msg_items)

    async def soft_delete_conversation(
        self, chat_session_id: UUID, account_type: str, account_id: int
    ) -> bool:
        success = await self.chat_repo.soft_delete_chat_session(
            chat_session_id=chat_session_id,
            account_type=account_type,
            account_id=account_id,
        )
        if not success:
            raise NotFoundError("Conversation not found or already deleted.")

        await self.audit_repo.record_event(
            action="CHAT_CONVERSATION_DELETED",
            actor_type=account_type,
            actor_id=account_id,
            entity_type="chat_session",
            entity_id=str(chat_session_id),
        )
        return True

    # ================= Message Exchange & AI Integration =================
    async def send_message_and_get_response(
        self,
        chat_session_id: UUID,
        account_type: str,
        account_id: int,
        user_prompt: str,
        request_id: Optional[str] = None,
    ) -> Tuple[Message, Message]:
        """Validate ownership, persist user prompt, query Gen AI, persist response."""
        # 1. Strict ownership and deletion check
        chat = await self.chat_repo.get_chat_session(
            chat_session_id=chat_session_id,
            account_type=account_type,
            account_id=account_id,
            allow_deleted=False,
        )
        if not chat:
            raise NotFoundError("Conversation not found or access denied.")

        # 2. Retrieve history to construct context for Gen AI
        previous_messages = await self.chat_repo.list_messages_for_chat(chat_session_id, limit=20)
        history = [
            {
                "role": "user" if m.sender.upper() == "USER" else "assistant",
                "content": m.content,
            }
            for m in previous_messages
            if m.status == "COMPLETED"
        ]

        # 3. Persist user message in PostgreSQL
        user_message = await self.chat_repo.create_message(
            chat_session_id=chat_session_id,
            sender="USER",
            content=user_prompt,
            status="COMPLETED",
        )

        # 4. If title is default, generate summary title from first prompt
        if chat.title in ("New Conversation", None):
            first_line = user_prompt.strip().split("\n")[0][:40]
            await self.chat_repo.update_chat_title(
                chat_session_id, account_type, account_id, title=first_line
            )

        # 5. Send inference request to Gen AI microservice
        ai_result: GenAIResult = await self.genai_client.generate_response(
            conversation_id=str(chat_session_id),
            message=user_prompt,
            conversation_history=history,
            request_id=request_id,
        )

        # 6. Persist assistant message in PostgreSQL
        assistant_message = await self.chat_repo.create_message(
            chat_session_id=chat_session_id,
            sender="ASSISTANT",
            content=ai_result.response_text,
            reply_to_message_id=user_message.message_id,
            status="COMPLETED",
            model_name=ai_result.model,
            input_tokens=ai_result.input_tokens,
            output_tokens=ai_result.output_tokens,
            response_time_ms=ai_result.response_time_ms,
        )

        return user_message, assistant_message
