from unittest.mock import patch

import pytest

from modules.m_auth.m_auth_postgres import connect_to_database


def test_missing_database_url_rejected(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        connect_to_database()


def test_database_connection_uses_environment_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/test_db",
    )

    with patch("modules.m_auth.m_auth_postgres.psycopg.connect") as mock_connect:
        connect_to_database()

        mock_connect.assert_called_once_with(
            "postgresql://test:test@localhost:5432/test_db",
            connect_timeout=5,
        )
