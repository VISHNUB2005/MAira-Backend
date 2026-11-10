# MAira Backend

Backend repository for **MAira**, an AI-powered conversational platform for an institutional portal.

This repository is the shared starting point for backend contributors. Read this file before changing the database or backend implementation. It is also written to be useful as context when supplied to an AI coding assistant.

> **Current documented scope:** PostgreSQL database bootstrap and team onboarding. Do not assume that an application framework, API contract, authentication implementation, or deployment setup is finalized unless it is documented in the relevant source files.

## 1. Start here

1. Read this README completely.
2. Check the current branch and pull the latest changes.
3. Read the database files under [database/](database/).
4. Set up your own local PostgreSQL database by following the steps below.
5. Before changing a table or column, discuss the change with the backend/database team and update the schema scripts and documentation together.

## 2. Repository layout

```text
MAira-Backend/
├── database/
│   ├── mira_db_schema.sql          # Creates the current database structure
│   ├── mira_db_update_existing.sql # Migration for an older imported schema
│   └── seed.example.sql            # Safe example seed; contains placeholder emails
├── README.md                       # Team setup guide and AI assistant context
└── .gitignore                      # Excludes local/private seed files and environments
```

The real team allowlist seed file is deliberately **not committed** because this repository is public and the file contains personal email addresses. Obtain the approved `database/seed.sql` from the team lead through the team's private channel. The repository ignores that local file.

## 3. Database overview

- Database name used in the local setup guide: `mira_db`
- PostgreSQL schema: `sch_con`
- Tested setup: PostgreSQL 18.6
- UUID defaults use PostgreSQL's native `pg_catalog.gen_random_uuid()`; the schema does not require the `uuid-ossp` extension.
- The schema script creates seven tables:

| Table | Purpose |
|---|---|
| `tb_con_user` | Approved student/faculty accounts and password hashes |
| `tb_con_admin` | Admin accounts and password hashes |
| `tb_con_user_sessions` | Authentication sessions; stores refresh-token hashes and revocation/expiry data |
| `tb_con_otp_verification` | OTP verification records, including OTP hash, purpose, expiry, attempts and verification/use timestamps |
| `tb_con_chat_sessions` | Chat conversation/session metadata |
| `tb_con_messages` | Messages belonging to chat sessions, including sender, content and model/usage metadata |
| `tb_con_audit_log` | Audit events for user/admin/system actions |

### Important distinction: two kinds of sessions

- `tb_con_user_sessions` is for **authentication sessions** (refresh-token hash, expiry and revocation).
- `tb_con_chat_sessions` is for **conversation history** (chat title, ownership reference and deletion state).

They solve different problems and should not be treated as the same session.

### Important relationship note

`tb_con_messages.chat_session_id` references `tb_con_chat_sessions.chat_session_id`. A chat session stores `account_type` and `account_id` to identify either a user or an admin. Because that is a polymorphic reference, the database schema does not declare one ordinary foreign key from `account_id` to both account tables. Backend code must validate that the referenced account exists and matches `account_type`.

## 4. Local setup — fresh database

Each developer should create and use a **local** database. Do not point every developer's application at one shared local PostgreSQL instance.

### Prerequisites

- PostgreSQL 18.6 (the version used to validate these scripts).
- PostgreSQL command-line tools, especially `psql`.
- Access to the approved team seed file if you need the real pre-approved account list.

Check the client version:

```bash
psql --version
```

### Step A — create the database

Run this while connected to the default `postgres` database:

```bash
psql -U postgres -d postgres -c "CREATE DATABASE mira_db;"
```

If the database already exists, do not create it again. If you intentionally need a completely fresh local copy, back up anything important first, then drop and recreate it.

**Windows PowerShell**, if `psql` is not on PATH:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d postgres -c "CREATE DATABASE mira_db;"
```

### Step B — create the schema

From the repository root:

```bash
psql -U postgres -d mira_db -f database/mira_db_schema.sql
```

Windows PowerShell:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d mira_db -f "database\mira_db_schema.sql"
```

### Step C — add development seed data

The public repository contains `database/seed.example.sql` with clearly fake `.invalid` email addresses. It is only an example.

For the actual project allowlist:

1. Obtain `seed.sql` from the team lead through the approved private channel.
2. Save it as `database/seed.sql`.
3. Do not commit or upload it to this public repository.
4. Run:

```bash
psql -U postgres -d mira_db -f database/seed.sql
```

If you are only testing locally and do not have the private team seed yet, copy `database/seed.example.sql` to `database/seed.sql`, review/replace its placeholder addresses, and then execute it.

Windows PowerShell:

```powershell
Copy-Item database\seed.example.sql database\seed.sql
# Edit database\seed.sql and replace every placeholder address first.
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d mira_db -f "database\seed.sql"
```

The seed inserts accounts with `password_hash = NULL`. It does not create demo passwords. Password creation belongs to the registration flow after successful OTP verification.

## 5. Existing database — migration path

Use `database/mira_db_update_existing.sql` **only** when your local database already has the older version of these tables and needs the agreed schema adjustments.

```bash
psql -U postgres -d mira_db -f database/mira_db_update_existing.sql
```

This migration:
- Allows `password_hash` to be NULL in the user and admin tables.
- Adds `name VARCHAR(150)` to the admin table if it is missing.
- Preserves existing records.

**Do not run the migration after creating a fresh database with `mira_db_schema.sql`.** The fresh schema already includes these changes.

## 6. Verify your local database

Connect:

```bash
psql -U postgres -d mira_db
```

List the tables:

```sql
\dt sch_con.*
```

Expected table count: **7**.

Check user accounts:

```sql
SELECT email, user_type, password_hash, status
FROM sch_con.tb_con_user
ORDER BY email;
```

Check admin accounts:

```sql
SELECT name, email, password_hash, status
FROM sch_con.tb_con_admin;
```

Check counts:

```sql
SELECT COUNT(*) AS total_users FROM sch_con.tb_con_user;
SELECT COUNT(*) AS total_admins FROM sch_con.tb_con_admin;
```

Exit psql:

```sql
\q
```

The exact counts depend on which seed file you ran.

## 7. Agreed account onboarding behaviour

The current intended user-account decision is:

1. User submits an email address.
2. Backend checks the allowlisted record in `sch_con.tb_con_user`.
3. If no matching record exists, do not allow self-registration.
4. If the account exists but `password_hash IS NULL`, begin the OTP-based registration/password-creation flow.
5. If the account exists and `password_hash IS NOT NULL`, route to the login flow.
6. Check account status as part of the decision. Only an `ACTIVE` account should proceed; handle `INACTIVE` and `LOCKED` according to the authentication policy.

This is application behaviour to implement and test; the SQL schema alone does not implement the API flow.

## 8. Security and collaboration rules

- Never store plaintext passwords. Store only a suitable password hash generated by the backend's approved password-hashing library.
- Never store plaintext OTP values; store OTP hashes and enforce expiry and attempt limits.
- Store refresh-token hashes, not raw refresh tokens.
- Do not commit `.env` files, credentials, private keys, real user email allowlists, production database dumps, or real user data.
- Use the ignored local file `database/seed.sql` for private seed data.
- Do not run destructive database commands against a shared or production database.
- Coordinate schema changes with the team before merging them.
- Keep SQL changes reviewable: update the fresh schema, migration path (when needed), and this documentation together.

## 9. Git workflow

Use a feature branch for changes. Do not commit directly to `main`.

Example:

```bash
git switch main
git pull origin main
git switch -c feature/your-change
# make and test your changes
git add .
git commit -m "Describe the change"
git push -u origin feature/your-change
```

Open a pull request into `main`, explain the change, and request review from the assigned reviewer. Do not merge your own change unless the team has explicitly agreed to that workflow.

## 10. Give this repository context to an AI assistant

When using ChatGPT, Copilot Chat, Gemini, Claude, or another coding assistant:

1. Load this README.
2. Load the relevant SQL file(s) from the `database/` directory.
3. If asking about application code, also provide the relevant source files; this README currently documents the database baseline, not every backend implementation detail.

Use this instruction:

> You are assisting with the MAira institutional conversational platform backend. Treat the supplied MAira README and repository files as the source of truth. First explain the existing design and the relevant code before proposing changes. Do not invent tables, columns, endpoints, environment variables, framework choices, or security behaviour that are not present in the supplied files. Clearly distinguish existing implementation from recommendations. Preserve the agreed PostgreSQL schema and registration rules. Never expose secrets or real user data. When suggesting a database change, explain its impact, provide a migration-safe SQL change, and identify the tests and documentation that must be updated. If required context is missing, ask for the specific file or decision instead of guessing.

---

**Team note:** This database setup is local development infrastructure. It does not connect the application backend to PostgreSQL yet. Backend connection configuration and health checks should be documented when that integration is implemented and reviewed.
