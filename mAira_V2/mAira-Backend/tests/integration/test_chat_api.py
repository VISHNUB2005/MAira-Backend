"""Integration tests for Chat and Conversation APIs."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.services.genai_service import GenAIResult


@pytest.mark.asyncio
async def test_chat_conversation_lifecycle(
    client: AsyncClient, student_auth_headers: dict
):
    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Introduction to AI"},
        headers=student_auth_headers,
    )
    assert create_res.status_code == 201
    conv_data = create_res.json()
    conv_id = conv_data["chat_session_id"]
    assert conv_data["title"] == "Introduction to AI"

    # 2. List conversations
    list_res = await client.get(
        "/api/v1/chat/conversations",
        headers=student_auth_headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(c["chat_session_id"] == conv_id for c in list_data["conversations"])

    # 3. Retrieve conversation detail
    detail_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=student_auth_headers,
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["conversation"]["chat_session_id"] == conv_id
    assert len(detail_data["messages"]) == 0

    # 4. Soft delete conversation
    del_res = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=student_auth_headers,
    )
    assert del_res.status_code == 200

    # 5. Accessing deleted conversation yields 404
    get_del = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=student_auth_headers,
    )
    assert get_del.status_code == 404


@pytest.mark.asyncio
async def test_send_message_with_mocked_genai(
    client: AsyncClient, student_auth_headers: dict
):
    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Machine Learning Query"},
        headers=student_auth_headers,
    )
    conv_id = create_res.json()["chat_session_id"]

    mock_result = GenAIResult(
        request_id="req-uuid-12345",
        response_text="Gradient descent is an optimization algorithm used to minimize loss.",
        model="local-llama3-rag",
        input_tokens=15,
        output_tokens=30,
        response_time_ms=120,
    )

    with patch(
        "app.services.genai_service.GenAIClient.generate_response",
        new=AsyncMock(return_value=mock_result),
    ):
        msg_res = await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"content": "What is gradient descent?"},
            headers=student_auth_headers,
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert msg_data["sender"] == "ASSISTANT"
        assert msg_data["status"] == "COMPLETED"
        assert "Gradient descent" in msg_data["content"]
        assert msg_data["model_name"] == "local-llama3-rag"
        assert msg_data["input_tokens"] == 15
        assert msg_data["output_tokens"] == 30

    # Verify conversation now contains both user prompt and assistant response
    detail_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=student_auth_headers,
    )
    messages = detail_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["sender"] == "USER"
    assert messages[0]["content"] == "What is gradient descent?"
    assert messages[1]["sender"] == "ASSISTANT"
    assert messages[1]["content"] == mock_result.response_text


@pytest.mark.asyncio
async def test_chat_canonical_sessions_lifecycle(
    client: AsyncClient, student_auth_headers: dict
):
    """Test canonical /api/v1/chat/sessions lifecycle."""
    # 1. Create session
    create_res = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Data Structures Study Session"},
        headers=student_auth_headers,
    )
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["chat_session_id"]
    assert session_data["title"] == "Data Structures Study Session"

    # 2. List sessions
    list_res = await client.get(
        "/api/v1/chat/sessions",
        headers=student_auth_headers,
    )
    assert list_res.status_code == 200
    assert any(s["chat_session_id"] == session_id for s in list_res.json()["conversations"])

    # 3. Post message
    mock_result = GenAIResult(
        request_id="req-canonical-1",
        response_text="A binary search tree maintains sorted keys for O(log n) lookups.",
        model="local-llama3-rag",
        input_tokens=10,
        output_tokens=20,
        response_time_ms=80,
    )
    with patch(
        "app.services.genai_service.GenAIClient.generate_response",
        new=AsyncMock(return_value=mock_result),
    ):
        msg_res = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "What is a binary search tree?"},
            headers=student_auth_headers,
        )
        assert msg_res.status_code == 200
        assert msg_res.json()["sender"] == "ASSISTANT"

    # 4. Get session detail
    detail_res = await client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers=student_auth_headers,
    )
    assert detail_res.status_code == 200
    assert len(detail_res.json()["messages"]) == 2

    # 5. Delete session
    del_res = await client.delete(
        f"/api/v1/chat/sessions/{session_id}",
        headers=student_auth_headers,
    )
    assert del_res.status_code == 200

    # 6. Verify deleted session gives 404
    get_del = await client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers=student_auth_headers,
    )
    assert get_del.status_code == 404


@pytest.mark.asyncio
async def test_send_message_when_genai_service_fails_returns_503(
    client: AsyncClient, student_auth_headers: dict
):
    """Verify that when Gen AI microservice is unreachable/times out, 503 is returned cleanly."""
    create_res = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Error Handling Test"},
        headers=student_auth_headers,
    )
    session_id = create_res.json()["chat_session_id"]

    from app.core.exceptions import GenAIServiceError

    with patch(
        "app.services.genai_service.GenAIClient.generate_response",
        side_effect=GenAIServiceError("AI service temporarily unavailable"),
    ):
        msg_res = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Hello AI?"},
            headers=student_auth_headers,
        )
        assert msg_res.status_code == 503
        data = msg_res.json()
        assert data["code"] == "AI_SERVICE_UNAVAILABLE"
        assert "temporarily unavailable" in data["message"].lower()
