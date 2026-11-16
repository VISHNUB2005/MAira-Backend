"""Gen AI Microservice HTTP Client with Managed Lifecycle and Connection Pooling."""

import asyncio
import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.exceptions import GenAIServiceError

logger = logging.getLogger("maira.genai")
settings = get_settings()


@dataclass
class GenAIResult:
    request_id: str
    response_text: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    response_time_ms: Optional[int] = None


class GenAIClient:
    """Asynchronous HTTP client for the independently deployed Gen AI inference microservice.

    Maintains a lifecycle-managed connection pool to prevent socket churn and ensure high concurrency.
    """

    _client: Optional[httpx.AsyncClient] = None

    def __init__(self):
        self.base_url = settings.GENAI_BASE_URL.rstrip("/")
        self.endpoint = f"{self.base_url}/api/v1/generate"
        self.timeout = httpx.Timeout(
            connect=settings.GENAI_CONNECT_TIMEOUT_SECONDS,
            read=settings.GENAI_READ_TIMEOUT_SECONDS,
            write=10.0,
            pool=10.0,
        )

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or initialize the persistent AsyncClient singleton with connection pooling."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=settings.GENAI_CONNECT_TIMEOUT_SECONDS,
                    read=settings.GENAI_READ_TIMEOUT_SECONDS,
                    write=10.0,
                    pool=10.0,
                ),
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                    keepalive_expiry=60.0,
                ),
            )
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        """Gracefully close connection pools upon application shutdown."""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None
            logger.info("Gen AI HTTP client connection pool closed.")

    async def generate_response(
        self,
        conversation_id: str,
        message: str,
        conversation_history: List[Dict[str, str]],
        request_id: Optional[str] = None,
    ) -> GenAIResult:
        """Send inference request to Gen AI microservice with correlation tracking and bounded retries."""
        req_id = request_id or str(uuid.uuid4())

        payload = {
            "request_id": req_id,
            "conversation_id": str(conversation_id),
            "message": message,
            "conversation_history": conversation_history,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Service-Auth": settings.GENAI_SERVICE_SECRET,
            "X-Request-ID": req_id,
        }

        start_time = time.perf_counter()
        client = await self.get_client()

        # Execute request with bounded retries for safe connection failures only
        for attempt in range(settings.GENAI_MAX_RETRIES + 1):
            try:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                )

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Process HTTP response
                if response.status_code == 200:
                    data = response.json()
                    return self._validate_and_parse_success(data, req_id, elapsed_ms)

                elif response.status_code >= 400:
                    try:
                        err_data = response.json()
                        err_code = err_data.get("error", {}).get("code", "AI_ERROR")
                        err_msg = err_data.get("error", {}).get("message", "Model error")
                    except Exception:
                        err_code = f"HTTP_{response.status_code}"
                        err_msg = "Inference service returned an error."

                    logger.warning(f"Gen AI returned error [{err_code}]: {err_msg} [req_id={req_id}]")
                    raise GenAIServiceError(message=err_msg, code=err_code)

            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                logger.warning(f"Gen AI connection attempt {attempt + 1} failed: {e}")
                if attempt < settings.GENAI_MAX_RETRIES:
                    # Exponential backoff with random jitter
                    backoff = (0.5 * (2 ** attempt)) + (secrets.SystemRandom().uniform(0.05, 0.15))
                    await asyncio.sleep(backoff)
                    continue
                raise GenAIServiceError(
                    message="The AI assistant is temporarily unavailable. Please try again shortly.",
                    code="AI_SERVICE_UNAVAILABLE",
                )

            except httpx.ReadTimeout as e:
                # Do NOT retry non-idempotent generation after read timeout
                logger.error(f"Gen AI read timeout [req_id={req_id}]: {e}")
                raise GenAIServiceError(
                    message="AI model response exceeded deadline. Please try a shorter query.",
                    code="GENAI_SERVICE_TIMEOUT",
                )

            except GenAIServiceError:
                raise

            except Exception as e:
                logger.error(f"Gen AI unexpected exception [req_id={req_id}]: {e}", exc_info=True)
                raise GenAIServiceError(
                    message="Unexpected error communicating with AI service.",
                    code="AI_COMMUNICATION_ERROR",
                )

        raise GenAIServiceError(
            message="The AI assistant is temporarily unavailable. Please try again shortly.",
            code="AI_SERVICE_UNAVAILABLE",
        )

    def _validate_and_parse_success(
        self, data: Dict[str, Any], expected_request_id: str, elapsed_ms: int
    ) -> GenAIResult:
        """Strictly validate Gen AI response structure and matching request ID."""
        if not isinstance(data, dict):
            raise GenAIServiceError("Malformed response received from AI service.", code="INVALID_AI_RESPONSE")

        # 1. Validate request_id correlation
        returned_req_id = data.get("request_id")
        if returned_req_id != expected_request_id:
            logger.error(
                f"Correlation mismatch: expected request_id='{expected_request_id}', "
                f"received='{returned_req_id}'"
            )
            raise GenAIServiceError("Correlation ID mismatch from AI service.", code="CORRELATION_ERROR")

        # 2. Check status
        if data.get("status") != "success":
            err_obj = data.get("error", {})
            err_msg = err_obj.get("message", "Inference error occurred.")
            err_code = err_obj.get("code", "AI_INFERENCE_FAILED")
            raise GenAIServiceError(err_msg, code=err_code)

        # 3. Extract payload
        response_text = data.get("response")
        if not response_text:
            raise GenAIServiceError("AI service returned empty response.", code="EMPTY_AI_RESPONSE")

        model_name = data.get("model", "local-rag-model")
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

        return GenAIResult(
            request_id=expected_request_id,
            response_text=response_text,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=elapsed_ms,
        )
