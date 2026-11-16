"""Create an isolated test database and apply the authoritative schema.

This script never connects to or modifies the configured application database.
It connects only to the PostgreSQL maintenance database to create TEST_DB_NAME,
then applies the schema to that test database.
"""

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.core.config import get_settings


def setup_test_db() -> None:
    settings = get_settings()
    test_db_name = settings.TEST_DB_NAME

    if test_db_name == "mira_db":
        raise RuntimeError("TEST_DB_NAME must not be mira_db.")

    schema_value = os.getenv("SCHEMA_SQL_PATH")
    schema_file = (
        Path(schema_value).expanduser().resolve()
        if schema_value
        else Path(__file__).resolve().parents[2] / "database" / "mira_db_schema.sql"
    )
    if not schema_file.is_file():
        raise FileNotFoundError(
            f"Authoritative schema file not found: {schema_file}. "
            "Set SCHEMA_SQL_PATH to the approved schema SQL file."
        )

    connection_args = {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
    }

    print(f"Checking isolated test database: {test_db_name}...")
    admin_conn = psycopg2.connect(dbname="postgres", **connection_args)
    admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (test_db_name,),
            )
            if not cursor.fetchone():
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db_name))
                )
                print(f"[OK] Created {test_db_name}")
            else:
                print(f"[INFO] {test_db_name} already exists")
    finally:
        admin_conn.close()

    test_conn = psycopg2.connect(dbname=test_db_name, **connection_args)
    test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with test_conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (settings.DB_SCHEMA,),
            )
            if cursor.fetchone():
                print(f"[INFO] Schema {settings.DB_SCHEMA} already exists; leaving it unchanged.")
                return

            print(f"[INFO] Applying schema to {test_db_name}...")
            lines = []
            for line in schema_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("\\restrict", "\\unrestrict")):
                    continue
                lines.append(line)
            cursor.execute("\n".join(lines))
            print(f"[OK] Applied schema to {test_db_name}")
    finally:
        test_conn.close()

    print("[SUCCESS] Isolated test database is ready.")


if __name__ == "__main__":
    try:
        setup_test_db()
    except Exception as exc:
        print(f"[ERROR] Test database setup failed: {exc}", file=sys.stderr)
        sys.exit(1)
