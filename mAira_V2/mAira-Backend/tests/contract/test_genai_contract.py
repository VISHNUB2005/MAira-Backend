"""Contract tests verifying the agreed proposed Backend–Gen AI microservice contract."""

import json
from unittest.mock import AsyncMock
import pytest
import httpx
from app.core.exceptions import GenAIServiceError
from app.services.genai_service import GenAIClient


@pytest.mark.asyncio
async def test_genai_success_contract():
    client = GenAIClient()
    req_id = "test-uuid-001"

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/generate"
        assert request.headers.get("X-Service-Auth") is not None
        body = json.loads(request.content)
        assert body["request_id"] == req_id
        assert body["conversation_id"] == "conv-001"
        assert body["message"] == "Explain transformers"
        assert len(body["conversation_history"]) == 2

        response_data = {
            "request_id": req_id,
            "status": "success",
            "response": "Transformers rely on the self-attention mechanism.",
            "model": "local-rag-v1",
            "usage": {
                "input_tokens": 120,
                "output_tokens": 180,
            },
        }
        return httpx.Response(status_code=200, json=response_data)

    transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.AsyncClient(transport=transport)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(GenAIClient, "get_client", AsyncMock(return_value=mock_http_client))

        result = await client.generate_response(
            conversation_id="conv-001",
            message="Explain transformers",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            request_id=req_id,
        )

        assert result.request_id == req_id
        assert "Transformers" in result.response_text
        assert result.model == "local-rag-v1"
        assert result.input_tokens == 120
        assert result.output_tokens == 180


@pytest.mark.asyncio
async def test_genai_error_contract():
    client = GenAIClient()
    req_id = "test-uuid-002"

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        error_payload = {
            "status": "error",
            "error": {
                "code": "MODEL_UNAVAILABLE",
                "message": "Local weights are currently reloading.",
            },
            "request_id": req_id,
        }
        return httpx.Response(status_code=503, json=error_payload)

    transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.AsyncClient(transport=transport)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(GenAIClient, "get_client", AsyncMock(return_value=mock_http_client))

        with pytest.raises(GenAIServiceError) as exc_info:
            await client.generate_response(
                conversation_id="conv-002",
                message="Explain RAG",
                conversation_history=[],
                request_id=req_id,
            )
        assert exc_info.value.code == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_genai_correlation_id_mismatch_detection():
    client = GenAIClient()
    req_id = "test-uuid-original"

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        response_data = {
            "request_id": "test-uuid-different",
            "status": "success",
            "response": "Spoofed response",
            "model": "rogue-model",
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
        return httpx.Response(status_code=200, json=response_data)

    transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.AsyncClient(transport=transport)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(GenAIClient, "get_client", AsyncMock(return_value=mock_http_client))

        with pytest.raises(GenAIServiceError) as exc_info:
            await client.generate_response(
                conversation_id="conv-003",
                message="Test correlation",
                conversation_history=[],
                request_id=req_id,
            )
        assert exc_info.value.code == "CORRELATION_ERROR"
