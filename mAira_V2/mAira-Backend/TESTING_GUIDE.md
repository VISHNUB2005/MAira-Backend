# MAIRA Phase 1 Backend — Testing & Quality Assurance Guide

This guide details the test architecture, automated test suites, execution procedures, isolation mechanics, and continuous security scanning practices for the MAIRA Phase 1 Backend.

---

## 1. Testing Philosophy & Test Suite Architecture

The MAIRA test suite is architected around the following foundational principles:
1. **100% Real PostgreSQL Verification**: Integration and security tests execute against real PostgreSQL instances (`mira_db`), exercising real database constraints, foreign keys, and indexes.
2. **Deterministic Transaction Rollback**: Tests execute inside scoped database transactions that automatically rollback at test teardown, preventing any state pollution or modification of pre-seeded records.
3. **External Microservice Decoupling**: External network boundaries (Gen AI microservice, SMTP servers) are decoupled via isolated test fixtures (`mock` EmailService outbox and monkeypatched `httpx.AsyncClient` handlers).
4. **Security & Tampering Coverage**: Dedicated test suites verify attack vectors, including IDOR, algorithm `none` JWT bypass, key confusion, token theft replay, and rate limit exhaustion.

```
tests/
├── conftest.py                   # Pytest fixtures, NullPool engine, test clients, mock services
├── unit/                         # Fast, in-memory unit tests
│   ├── test_otp.py               # Cryptographic OTP generation, email salting, attempt counters
│   ├── test_permissions.py       # RBAC role validation, immutability, permission mappings
│   ├── test_schemas.py           # Pydantic schemas, password complexity validation
│   ├── test_security.py          # Bcrypt hashing, NULL-hash timing mitigation, redaction
│   └── test_tokens.py            # JWT claims, refresh token hashing, registration tickets
├── integration/                  # End-to-end API route tests with PostgreSQL
│   ├── test_auth_api.py          # Complete registration, login, refresh, theft detection, logout
│   ├── test_admin_api.py         # Student onboarding, status toggling, admin authorization
│   ├── test_user_api.py          # Authenticated user profiles, unauthenticated rejection
│   └── test_chat_api.py          # Conversation CRUD, message ordering, Gen AI response persistence
├── security/                     # Dedicated penetration & vulnerability tests
│   ├── test_idor.py              # Cross-user conversation isolation, privilege escalation
│   ├── test_security_controls.py # Security headers, X-Request-ID propagation, rate limiting
│   ├── test_token_tampering.py   # None-algorithm attack, wrong secret keys, invalid aud/iss
│   └── test_unauthorized_access.py # Missing/malformed tokens, invalid bearer headers
└── contract/                     # Microservice contract verification
    └── test_genai_contract.py    # POST /api/v1/generate headers, correlation IDs, retries
```

---

## 2. Test Environment Isolation Mechanics (`tests/conftest.py`)

### 2.1. The `NullPool` Connection Strategy
In `pytest-asyncio`, tests run in isolated event loops. Persistent connection pools across function-scoped event loops trigger `RuntimeError: Event loop is closed`.

The test configuration overrides the engine with `NullPool`:
```python
test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    echo=False
)
```
Each database session checked out by `db_session` executes within an atomic transaction. Upon fixture teardown, the transaction is explicitly rolled back:
```python
@pytest_asyncio.fixture
async def db_session():
    async with test_session_factory() as session:
        yield session
        await session.rollback()
```
This guarantees that seeded institutional records are never modified, and newly created test entities are cleanly discarded.

---

## 3. Executing the Test Suites

Execute all tests from the repository root:

### 3.1. Run Full Test Suite
```bash
python -m pytest tests/ -v
```

### 3.2. Run Specific Test Layers
```bash
# Unit Tests Only
python -m pytest tests/unit/ -v

# Integration Tests Only
python -m pytest tests/integration/ -v

# Security & Penetration Tests Only
python -m pytest tests/security/ -v

# Contract Tests Only
python -m pytest tests/contract/ -v
```

### 3.3. Run with Short Tracebacks
```bash
python -m pytest tests/ -v --tb=short
```

---

## 4. Current Test Results Summary

| Test Suite | Total Tests | Passed | Failed | Execution Time |
|---|:---:|:---:|:---:|:---:|
| **Contract** (`tests/contract/`) | 3 | 3 | 0 | ~1.2s |
| **Integration** (`tests/integration/`) | 8 | 8 | 0 | ~8.4s |
| **Security** (`tests/security/`) | 14 | 14 | 0 | ~5.8s |
| **Unit** (`tests/unit/`) | 20 | 20 | 0 | ~4.7s |
| **Total** | **45** | **45** | **0** | **~20.1s** |

**Pass Rate**: **100% (45 of 45 tests passing)**.

---

## 5. Automated Security Scanning

### 5.1. Static Application Security Testing (Bandit)
Run Bandit to scan for common security risks, insecure imports, and credential exposures:
```bash
python -m bandit -r app/ -ll
```
*Expected Result*: 0 High, 0 Medium issues.

### 5.2. Dependency Vulnerability Auditing (pip-audit)
Scan third-party packages against known vulnerability databases:
```bash
python -m pip_audit
```
*Note*: As detailed in `SECURITY.md`, `python-jose` includes an advisory for `ecdsa` which is not exercised by MAIRA's HS256 token verification. Phase 2 roadmap replaces `python-jose` with `PyJWT`.
