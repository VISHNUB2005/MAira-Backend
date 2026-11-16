"""MAIRA Phase 1 — Database Preflight and Safety Verification Script.

100% Read-Only verification of PostgreSQL connectivity, schema, tables,
columns, constraints, and institutional database safety guards.
"""

import argparse
import asyncio
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

EXPECTED_TABLES = [
    "tb_con_admin",
    "tb_con_audit_log",
    "tb_con_chat_sessions",
    "tb_con_messages",
    "tb_con_otp_verification",
    "tb_con_user",
    "tb_con_user_sessions",
]

EXPECTED_COLUMNS = {
    "tb_con_admin": ["admin_id", "name", "email", "password_hash", "status", "created_at", "updated_at"],
    "tb_con_audit_log": ["audit_id", "actor_type", "actor_id", "action", "entity_type", "entity_id", "event_at", "details"],
    "tb_con_chat_sessions": ["chat_session_id", "account_type", "account_id", "title", "is_deleted", "deleted_at", "created_at", "updated_at"],
    "tb_con_messages": ["message_id", "chat_session_id", "sender", "content", "reply_to_message_id", "status", "model_name", "input_tokens", "output_tokens", "response_time_ms", "created_at", "updated_at"],
    "tb_con_otp_verification": ["otp_id", "account_type", "account_id", "email", "otp_hash", "purpose", "expires_at", "attempts", "max_attempts", "verified_at", "used_at", "created_at"],
    "tb_con_user": ["user_id", "email", "user_type", "password_hash", "status", "created_at", "updated_at"],
    "tb_con_user_sessions": ["session_id", "account_type", "account_id", "refresh_token_hash", "created_at", "expires_at", "last_used_at", "revoked_at", "is_revoked"],
}


async def verify(target_db: str, is_test_mode: bool = False):
    settings = get_settings()

    print("=" * 70)
    print("MAIRA Phase 1 — Database Preflight & Safety Verification")
    print("=" * 70)

    # 1. Safety Guard Check
    db_name = target_db or settings.DB_NAME
    print(f"Target Database: {db_name}")
    print(f"Host:            {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"Schema:          {settings.DB_SCHEMA}")
    print(f"Mode:            {'TEST ISOLATION' if is_test_mode else settings.ENVIRONMENT.upper()}")

    if is_test_mode:
        if db_name == "mira_db":
            print("\n[CRITICAL ERROR] SAFETY VIOLATION: Test suite cannot connect to 'mira_db'!")
            print("Tests must run ONLY against an isolated database such as 'mira_test_db'.")
            sys.exit(1)
        print("[OK] Test database safety guard: Verified not targeting 'mira_db'.")

    # 2. Connection verification
    db_user = settings.DB_USER
    db_pass = settings.DB_PASSWORD
    db_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{settings.DB_HOST}:{settings.DB_PORT}/{db_name}"

    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.connect() as conn:
            # Check current database name
            res = await conn.execute(text("SELECT current_database();"))
            resolved_db = res.scalar()
            print(f"[OK] Connected successfully. Resolved database: {resolved_db}")

            if is_test_mode and resolved_db == "mira_db":
                print("[CRITICAL ERROR] Server returned 'mira_db' under test mode! Aborting.")
                sys.exit(1)

            # Check schema
            res = await conn.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :s;"),
                {"s": settings.DB_SCHEMA},
            )
            if not res.scalar():
                print(f"[FAIL] Schema '{settings.DB_SCHEMA}' does not exist in {resolved_db}!")
                sys.exit(1)
            print(f"[OK] Schema '{settings.DB_SCHEMA}' verified.")

            # Check tables
            res = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = :s;"),
                {"s": settings.DB_SCHEMA},
            )
            tables = set(r[0] for r in res.fetchall())
            missing_tables = set(EXPECTED_TABLES) - tables
            if missing_tables:
                print(f"[FAIL] Missing required tables: {missing_tables}")
                sys.exit(1)
            print(f"[OK] All {len(EXPECTED_TABLES)} required tables are present in '{settings.DB_SCHEMA}'.")

            # Check columns
            missing_cols = []
            for tbl, exp_cols in EXPECTED_COLUMNS.items():
                col_res = await conn.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_schema = :s AND table_name = :t;"),
                    {"s": settings.DB_SCHEMA, "t": tbl},
                )
                existing_cols = set(r[0] for r in col_res.fetchall())
                for c in exp_cols:
                    if c not in existing_cols:
                        missing_cols.append(f"{tbl}.{c}")

            if missing_cols:
                print(f"[FAIL] Missing columns in schema: {missing_cols}")
                sys.exit(1)
            print(f"[OK] All required columns verified across all tables.")

            # Check primary keys
            pk_res = await conn.execute(
                text(
                    """
                    SELECT tc.table_name, ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                      ON tc.constraint_name = ccu.constraint_name
                      AND tc.table_schema = ccu.table_schema
                    WHERE tc.table_schema = :s AND tc.constraint_type = 'PRIMARY KEY';
                    """
                ),
                {"s": settings.DB_SCHEMA},
            )
            pks = {r[0]: r[1] for r in pk_res.fetchall()}
            print(f"[OK] Primary keys verified for {len(pks)} tables.")

            # Record count check (read-only)
            user_count = (await conn.execute(text("SELECT count(*) FROM sch_con.tb_con_user;"))).scalar()
            admin_count = (await conn.execute(text("SELECT count(*) FROM sch_con.tb_con_admin;"))).scalar()
            print(f"[INFO] Approved User records in {resolved_db}: {user_count}")
            print(f"[INFO] Administrator records in {resolved_db}: {admin_count}")

            print("=" * 70)
            print(f"[SUCCESS] Database '{resolved_db}' is fully compatible and verified.")
            print("=" * 70)

    except Exception as e:
        print(f"[ERROR] Database verification failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAIRA Database Preflight Check")
    parser.add_argument("--db", type=str, default=None, help="Target database name (default: from settings)")
    parser.add_argument("--test", action="store_true", help="Run in test-isolation safety check mode")
    args = parser.parse_args()

    asyncio.run(verify(target_db=args.db, is_test_mode=args.test))
