# MAIRA Phase 1 Backend

MAIRA is an institutional conversational AI platform. This repository contains the complete, production-grade Phase 1 backend built with FastAPI, SQLAlchemy 2.0, PostgreSQL 18.6, and bcrypt, integrating with an independently deployed local Gen AI inference microservice.

---

## Key Features

- **Administrator-Controlled Registration**: Pre-approved institutional email allowlist verification, cryptographically secure single-use OTP dispatch, bcrypt password hashing, and audit logging.
- **Robust Authentication & Session Management**: Bcrypt password verification, MFA readiness, signed JWT access tokens (15-min lifespan), opaque 64-byte refresh tokens with SHA-256 hash persistence, and atomic refresh token rotation with reuse/theft detection.
- **Granular RBAC Authorization**: Enforces role and permission checks across `ADMIN`, `STUDENT`, and `FACULTY` roles.
- **Chat & Conversation Management**: Conversation lifecycle management, strict ownership validation (`account_type` and `account_id`), soft-deletion, and PostgreSQL persistence.
- **Independent Gen AI Microservice Integration**: Resilient asynchronous HTTP client communicating with local LLM/RAG microservice via `POST /api/v1/generate`, with request correlation (`request_id`), bounded retries, timeouts, and safe error mapping. Gen AI is strictly isolated from PostgreSQL.
- **Centralized Security Hardening**: Defense-in-depth security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options), strict CORS allowlist, in-memory sliding window rate limiting on sensitive routes, sensitive data redaction, and centralized secrets provider.

---

## Technology Stack

- **Framework**: Python 3.14+, FastAPI 0.115+, Pydantic v2
- **Database**: PostgreSQL 18.6 (`mira_db`), Schema `sch_con`
- **ORM & Driver**: SQLAlchemy 2.0 (async), `asyncpg` (async engine), `psycopg2-binary` (sync utilities)
- **Cryptography**: `bcrypt` (12 rounds), `python-jose` (HS256 JWTs), `hashlib` (SHA-256)
- **Testing**: `pytest`, `pytest-asyncio`, `httpx` (ASGITransport), `bandit`, `pip-audit`

---

## Directory Structure

```text
mAira-Backend/
├── app/
│   ├── main.py                          # FastAPI entrypoint, middleware, router mounts, lifespan
│   ├── core/
│   │   ├── config.py                    # Typed Pydantic Settings with env/secret loading
│   │   ├── database.py                  # SQLAlchemy engine, session maker, connection pool
│   │   ├── security.py                  # Bcrypt hashing, token helpers, crypto utilities
│   │   └── exceptions.py                # Custom exceptions and centralized exception handlers
│   ├── api/
│   │   ├── dependencies.py              # Auth, DB session, role, and permission dependencies
│   │   └── v1/
│   │       ├── auth.py                  # Register, verify-OTP, set-password, login, MFA, refresh, logout
│   │       ├── users.py                 # Profile retrieval
│   │       ├── admin.py                 # Admin student management, status toggling, analytics
│   │       └── chat.py                  # Conversation CRUD, message submission, AI interaction
│   ├── models/                          # SQLAlchemy models for sch_con schema
│   │   ├── user.py                      # tb_con_user
│   │   ├── admin.py                     # tb_con_admin
│   │   ├── session.py                   # tb_con_user_sessions
│   │   ├── otp.py                       # tb_con_otp_verification
│   │   ├── chat.py                      # tb_con_chat_sessions
│   │   ├── message.py                   # tb_con_messages
│   │   └── audit.py                     # tb_con_audit_log
│   ├── repositories/                    # Type-safe database query repositories
│   ├── services/                        # Business logic services (auth, otp, email, chat, genai)
│   ├── security/                        # RBAC permissions, middleware, secrets, rate limiter, audit
│   └── utils/                           # Sensitive data redaction and masking
├── tests/
│   ├── unit/                            # Unit tests for security, tokens, schemas, permissions
│   ├── integration/                     # Full API lifecycle integration tests
│   ├── contract/                        # Contract tests matching Gen AI microservice schema
│   └── security/                        # Security tests for IDOR, token tampering, headers, rate limits
├── scripts/
│   ├── run_dev.py                       # Development server runner with preflight checks
│   └── verify_db.py                     # Safe read-only database connectivity verification
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Quick Start

### 1. Prerequisites

- Python 3.14+ installed.
- PostgreSQL 18.6 running locally with database `mira_db` initialized with schema `sch_con`.

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Ensure `DB_PASSWORD` and `JWT_SECRET_KEY` (at least 32 bytes) are configured.

### 3. Verify Database Preflight

Run the safe verification script:

```bash
python scripts/verify_db.py
```

### 4. Run Automated Test Suite

Run all 45 automated tests (unit, integration, contract, security):

```bash
python -m pytest tests/ -v
```

### 5. Launch Application Server

```bash
python scripts/run_dev.py
```

The server will be accessible at `http://127.0.0.1:8000`.
Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

---

## Documentation Index

1. [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture, layer responsibilities, data flow.
2. [API_DOCUMENTATION.md](API_DOCUMENTATION.md) — Complete API endpoints, contracts, request/response formats.
3. [DATABASE_INTEGRATION.md](DATABASE_INTEGRATION.md) — `sch_con` table mapping, pooling, query patterns.
4. [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md) — Registration, Login, MFA, JWT, Refresh token lifecycle.
5. [GENAI_INTEGRATION.md](GENAI_INTEGRATION.md) — Backend–Gen AI contract, timeouts, bounded retries, error mapping.
6. [SECURITY.md](SECURITY.md) — Defense-in-depth, secrets management, CORS, audit, rate limiting.
7. [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) — Local development & production setup guide.
8. [TESTING_GUIDE.md](TESTING_GUIDE.md) — Running unit, integration, contract, and security tests.
9. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — Production readiness checklist, systemd/Docker, secrets, backups.


## Single email-entry authentication

The frontend uses `POST /api/v1/auth/identify` before initiating registration or password login. The endpoint returns `REGISTER` for an active approved account with `password_hash IS NULL`, and `LOGIN` for an active account with a password hash. Unknown or inactive accounts receive a generic not-eligible response. The endpoint is rate-limited.

For local Vite development, set `CORS_ALLOW_ORIGINS_RAW` in `.env` to include `http://localhost:5173,http://127.0.0.1:5173`. This setting is named `CORS_ALLOW_ORIGINS_RAW` in the current Pydantic settings model.

**Database safety:** use `DB_NAME=mira_test_db` for local write-based integration testing. Do not run registration, OTP, password creation, chat, or admin pre-approval tests against the institutional `mira_db`.
