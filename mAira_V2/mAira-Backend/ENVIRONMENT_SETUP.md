# MAIRA Phase 1 Backend — Environment Setup Guide

This guide provides step-by-step instructions for configuring, initializing, and verifying the MAIRA Phase 1 Backend in a local development or staging environment.

---

## 1. System Prerequisites

Before starting the setup, ensure your host environment satisfies the following requirements:

| Component | Minimum Version | Recommended Version | Notes |
|---|---|---|---|
| **Operating System** | Windows 10/11, Linux (Ubuntu 22.04+), macOS 13+ | Windows 11 / Ubuntu 24.04 LTS | Tested on Windows 11 with PowerShell |
| **Python** | 3.11+ | 3.14.x | Standard CPython distribution |
| **PostgreSQL** | 15+ | 18.6 | Target database `mira_db` with schema `sch_con` |
| **Git** | 2.30+ | Latest | Version control |

---

## 2. PostgreSQL Database Verification

MAIRA Phase 1 utilizes the existing institutional database `mira_db` under schema `sch_con`.

1. Ensure the PostgreSQL service is active on `localhost:5432`.
2. Confirm the database `mira_db` and user account exist.
3. Test connectivity via `psql`:
   ```bash
   psql -U postgres -h 127.0.0.1 -d mira_db
   ```
4. Confirm schema `sch_con` is present:
   ```sql
   SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'sch_con';
   ```

> [!CAUTION]
> **Preservation Rule**: Do not run `DROP SCHEMA`, `DROP TABLE`, or `TRUNCATE` commands. The database already contains 18 approved institutional student accounts and 1 administrator account.

---

## 3. Local Python Environment Setup

### 3.1. Clone and Navigate to the Repository
```bash
cd c:\Dev\mAira\mAira-Backend
```

### 3.2. Create and Activate Virtual Environment (Recommended)
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
On Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3.3. Install Project Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> [!NOTE]
> **Windows Python 3.14 Note**: On certain Windows environments with Application Control (WDAC/AppLocker), newly compiled Cython `.pyd` files inside `AppData\Local` may be blocked from loading. If you encounter an `ImportError: DLL load failed while importing _collections_cy`, renaming `*.pyd` files in `site-packages\sqlalchemy` to `*.pyd.disabled` allows SQLAlchemy to cleanly utilize its native pure-Python modules with zero loss in functionality.

---

## 4. Environment Configuration (`.env`)

Copy the sanitized template `.env.example` to create your local `.env`:
```powershell
Copy-Item .env.example .env
```

### Configuration Variables Breakdown

```ini
# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
APP_HOST=127.0.0.1
APP_PORT=8000

# PostgreSQL Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_local_postgres_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=mira_db
POSTGRES_SCHEMA=sch_con

# Database Connection Pool Tuning
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# JWT & Authentication Secrets
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=generate_a_cryptographically_secure_random_key_min_32_chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=maira-backend
JWT_AUDIENCE=maira-frontend

# Registration & OTP Parameters
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=5
OTP_MAX_ATTEMPTS=5
REGISTRATION_TICKET_EXPIRE_MINUTES=10

# Transactional Email Dispatcher
# Options: 'mock' (in-memory for tests), 'console' (prints to terminal for dev), 'smtp' (production)
EMAIL_PROVIDER=console
SMTP_HOST=smtp.institution.edu
SMTP_PORT=587
SMTP_USER=no-reply@institution.edu
SMTP_PASSWORD=smtp_secret_password
SMTP_FROM_EMAIL=no-reply@institution.edu
SMTP_USE_TLS=true

# Gen AI Microservice Integration
GENAI_SERVICE_URL=http://localhost:8001
GENAI_SERVICE_KEY=generate_a_secure_shared_secret_for_microservice
GENAI_CONNECT_TIMEOUT=5.0
GENAI_READ_TIMEOUT=30.0
GENAI_MAX_RETRIES=2

# Security Headers & CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
RATE_LIMIT_ENABLED=true
```

---

## 5. Preflight Verification & Health Check

Before launching the backend server, execute the preflight verification script:
```bash
python scripts/verify_db.py
```

Expected output:
```
============================================================
MAIRA Phase 1 — Database Preflight Verification
============================================================
Checking connection to PostgreSQL mira_db...
[OK] Connection established successfully.

[OK] Found 7 tables in schema 'sch_con':
  - sch_con.tb_con_admin
  - sch_con.tb_con_audit_log
  - sch_con.tb_con_chat_sessions
  - sch_con.tb_con_messages
  - sch_con.tb_con_otp_verification
  - sch_con.tb_con_user
  - sch_con.tb_con_user_sessions

[INFO] Total approved user records in database: 18
[INFO] Total administrator records in database: 1

[SUCCESS] mira_db is ready for application use.
```

---

## 6. Running the Development Server

Start the application using the bundled development runner:
```bash
python scripts/run_dev.py
```
Or directly with Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Accessing Interactive API Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
