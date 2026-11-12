"""PostgreSQL connection helper for Group 2."""

import os

import psycopg


def connect_to_database():
    """Open a PostgreSQL connection using DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        database_url,
        connect_timeout=5,
    )
