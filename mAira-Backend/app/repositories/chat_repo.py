"""Chat Session and Messages repository."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession
from app.models.message import Message


class ChatRepository:
    """Repository for sch_con.tb_con_chat_sessions and sch_con.tb_con_messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ================= Chat Sessions =================
    async def create_chat_session(
        self, account_type: str, account_id: int, title: Optional[str] = None
    ) -> ChatSession:
        chat = ChatSession(
            account_type=account_type.upper(),
            account_id=account_id,
            title=title or "New Conversation",
            is_deleted=False,
        )
        self.session.add(chat)
        await self.session.flush()
        return chat

    async def get_chat_session(
        self,
        chat_session_id: UUID,
        account_type: str,
        account_id: int,
        allow_deleted: bool = False,
    ) -> Optional[ChatSession]:
        """Fetch chat session strictly enforcing ownership."""
        stmt = select(ChatSession).where(
            ChatSession.chat_session_id == chat_session_id,
            ChatSession.account_type == account_type.upper(),
            ChatSession.account_id == account_id,
        )
        if not allow_deleted:
            stmt = stmt.where(ChatSession.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_chat_sessions(
        self,
        account_type: str,
        account_id: int,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> List[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.account_type == account_type.upper(),
                ChatSession.account_id == account_id,
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if not include_deleted:
            stmt = stmt.where(ChatSession.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_chat_title(
        self, chat_session_id: UUID, account_type: str, account_id: int, title: str
    ) -> Optional[ChatSession]:
        chat = await self.get_chat_session(chat_session_id, account_type, account_id)
        if chat:
            chat.title = title.strip()[:255]
            await self.session.flush()
        return chat

    async def soft_delete_chat_session(
        self, chat_session_id: UUID, account_type: str, account_id: int
    ) -> bool:
        stmt = (
            update(ChatSession)
            .where(
                ChatSession.chat_session_id == chat_session_id,
                ChatSession.account_type == account_type.upper(),
                ChatSession.account_id == account_id,
                ChatSession.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    # ================= Messages =================
    async def create_message(
        self,
        chat_session_id: UUID,
        sender: str,
        content: str,
        reply_to_message_id: Optional[UUID] = None,
        status: str = "COMPLETED",
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        response_time_ms: Optional[int] = None,
    ) -> Message:
        msg = Message(
            chat_session_id=chat_session_id,
            sender=sender.upper(),
            content=content,
            reply_to_message_id=reply_to_message_id,
            status=status.upper(),
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=response_time_ms,
        )
        self.session.add(msg)
        # Touch chat session updated_at
        touch_stmt = (
            update(ChatSession)
            .where(ChatSession.chat_session_id == chat_session_id)
            .values(updated_at=func.now())
        )
        await self.session.execute(touch_stmt)
        await self.session.flush()
        return msg

    async def list_messages_for_chat(
        self, chat_session_id: UUID, limit: int = 100
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.chat_session_id == chat_session_id)
            .order_by(Message.created_at.asc(), Message.reply_to_message_id.nulls_first())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
