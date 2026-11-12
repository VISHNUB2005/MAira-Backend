# MAIRA Phase 1 Backend — Gen AI Microservice Integration Guide

This document specifies the integration architecture, network contract, client configuration, and security boundaries between the MAIRA Phase 1 Backend and the independent Gen AI microservice.

---

## 1. Architectural Boundary & Security Model

The MAIRA Backend integrates with an external, independently deployed Gen AI microservice (e.g. running PyTorch, vLLM, or Ollama behind FastAPI).

```
+───────────────────────────+                 +───────────────────────────+
|    MAIRA BACKEND          |                 |   GEN AI MICROSERVICE     |
|    (Port 8000)            |                 |   (Port 8001)             |
|                           |  POST /generate |                           |
|  - Manages PostgreSQL     |────────────────>|  - Stateless inference    |
|  - Enforces RBAC & IDOR   |  X-Service-Auth |  - No database connection |
|  - Sanitizes prompts      |  X-Request-ID   |  - Token generation       |
|  - Persists chat history  |<────────────────|                           |
+───────────────────────────+  JSON Response  +───────────────────────────+
              │
              ▼
   PostgreSQL 18.6 (mira_db)
```

### Strict Security Boundaries
1. **Zero Database Access**: The Gen AI microservice has **zero database access, zero database credentials, and no network route to PostgreSQL**.
2. **Context Ownership**: The backend is solely responsible for querying `sch_con.tb_con_messages`, filtering for user ownership, assembling the context window, and passing only necessary history.
3. **Mutual Service Authentication**: Requests to the Gen AI microservice are secured via a high-entropy pre-shared key transmitted in the `X-Service-Auth` header.
4. **Data Redaction**: Sensitive account fields (emails, registration numbers, user IDs) are never sent to the Gen AI service. Only chat turn roles and message contents are transmitted.

---

## 2. API Contract Specification

### 2.1. Generation Request: `POST /api/v1/generate`

#### Request Headers
| Header | Value | Purpose |
|---|---|---|
| `Content-Type` | `application/json` | Media type |
| `X-Service-Auth` | `<GENAI_SERVICE_KEY>` | Shared secret service authentication |
| `X-Request-ID` | `req_<uuid>` | End-to-end distributed tracing correlation ID |

#### Request Payload
```json
{
  "prompt": "Explain the difference between synchronous and asynchronous database engines.",
  "conversation_history": [
    {
      "role": "user",
      "content": "What is SQLAlchemy?"
    },
    {
      "role": "assistant",
      "content": "SQLAlchemy is the Python SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL."
    }
  ],
  "request_id": "req_8f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 0.95
  }
}
```

---

### 2.2. Generation Response: `200 OK`

#### Response Body
```json
{
  "content": "Synchronous database engines block the executing thread while waiting for I/O operations to complete, whereas asynchronous engines yield control to the event loop, enabling a single process to handle high concurrency with low memory footprint.",
  "model_version": "llama-3-8b-instruct-q4",
  "token_count": 42,
  "correlation_id": "req_8f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

---

## 3. Client Implementation & Resilience (`app/services/genai_client.py`)

The backend interacts with the Gen AI service via an asynchronous `httpx.AsyncClient` singleton configured for high concurrency and resilience.

### 3.1. Connection Pooling & Timeouts
```python
client = httpx.AsyncClient(
    base_url=settings.GENAI_SERVICE_URL,
    timeout=httpx.Timeout(
        connect=5.0,     # Maximum time to establish TCP handshake (5s)
        read=30.0,       # Inference computation deadline (30s)
        write=10.0,      # Request transmission deadline (10s)
        pool=35.0        # Total lifecycle timeout (35s)
    ),
    limits=httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20,
        keepalive_expiry=60.0
    )
)
```

### 3.2. Correlation ID Enforcement
To prevent cross-request race conditions or response swapping in high-concurrency microservice proxies:
```python
if response_data.get("correlation_id") != outgoing_request_id:
    logger.error("Gen AI response correlation ID mismatch")
    raise GenAIServiceError(
        status_code=502,
        code="CORRELATION_ID_MISMATCH",
        message="Upstream AI service returned mismatched correlation identifier."
    )
```

### 3.3. Retry Policy with Exponential Backoff
- **Max Retries**: 2 retries (3 total attempts).
- **Backoff Interval**: $0.5\text{s} \times 2^{\text{attempt}}$ with random jitter ($\pm 100\text{ms}$).
- **Retry Conditions**:
  - `httpx.ConnectError` (temporary network glitch).
  - `httpx.ConnectTimeout` (microservice pod starting up).
  - HTTP `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`.
- **Non-Retry Conditions**:
  - HTTP `4xx` client errors (e.g. `400 Bad Request`, `401 Unauthorized`, `422 Unprocessable Entity`). Immediate failure without retry.

---

## 4. Error Mapping & Graceful Degradation

The backend translates all upstream Gen AI failures into safe, sanitized client responses without exposing internal service URLs, ports, or API keys:

| Gen AI Failure Condition | HTTP Status to Client | Application Error Code | Client Message |
|---|---|---|---|
| HTTP 401 / 403 (Invalid Service Key) | `500 Internal Server Error` | `GENAI_AUTH_CONFIG_ERROR` | `"AI service configuration error. Please contact administrator."` |
| HTTP 502 / 503 / Connect Failure | `502 Bad Gateway` | `GENAI_SERVICE_UNAVAILABLE` | `"AI generation service is temporarily unavailable. Please try again shortly."` |
| HTTP 504 / Read Timeout (> 30s) | `504 Gateway Timeout` | `GENAI_SERVICE_TIMEOUT` | `"AI model response exceeded deadline. Please try a shorter query."` |
| Malformed JSON / Schema Mismatch | `502 Bad Gateway` | `GENAI_RESPONSE_INVALID` | `"Unexpected response structure from upstream AI service."` |
| Correlation ID Mismatch | `502 Bad Gateway` | `CORRELATION_ID_MISMATCH` | `"Upstream AI service correlation failure."` |

---

## 5. Local Mocking for Automated Testing (`tests/contract/test_genai_contract.py`)

During automated testing and continuous integration, external dependencies are decoupled using HTTP mocking. The test suite verifies:
1. Exact serialization of request headers (`X-Service-Auth`, `X-Request-ID`) and payload structures.
2. Handling of model timeouts and HTTP error codes.
3. Detection and rejection of mismatched `correlation_id` tokens.
