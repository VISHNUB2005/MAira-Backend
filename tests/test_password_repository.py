from unittest.mock import MagicMock

import pytest

from modules.m_auth.m_auth_password_repository import (
    PostgresUserPasswordRepository,
)


def make_repository(rowcount=1, token_inserted=True):
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = rowcount

    cursor.fetchone.return_value = ("test-jti-123",) if token_inserted else None

    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    repository = PostgresUserPasswordRepository(
        connection_factory=lambda: connection,
    )

    return repository, connection, cursor


def test_password_update_uses_actual_database_schema():
    repository, connection, cursor = make_repository()

    result = repository.complete_password_setup(
        "student@example.com",
        "$argon2id$example-hash",
        "test-jti-123",
        1794390044,
    )

    assert result is True
    assert cursor.execute.call_count == 2

    insert_query, insert_params = cursor.execute.call_args_list[0].args
    update_query, update_params = cursor.execute.call_args_list[1].args

    assert "INSERT INTO sch_con.tb_con_registration_token_usage" in insert_query
    assert "ON CONFLICT (jti) DO NOTHING" in insert_query
    assert insert_params == (
        "test-jti-123",
        "student@example.com",
        1794390044,
        1794390044,
    )

    assert "UPDATE sch_con.tb_con_user" in update_query
    assert "SET password_hash = %s" in update_query
    assert "LOWER(email) = LOWER(%s)" in update_query
    assert "status = 'ACTIVE'" in update_query
    assert "password_hash IS NULL" in update_query
    assert "status =" not in update_query.split("WHERE")[0]

    assert update_params == (
        "$argon2id$example-hash",
        "student@example.com",
    )
    connection.close.assert_called_once()


def test_missing_or_ineligible_user_returns_false():
    repository, _, cursor = make_repository(rowcount=0)

    assert repository.complete_password_setup(
        "student@example.com",
        "$argon2id$example-hash",
        "test-jti-123",
        1794390044,
    ) is False

    assert cursor.execute.call_count == 2


def test_replayed_token_returns_false():
    repository, _, cursor = make_repository(token_inserted=False)

    assert repository.complete_password_setup(
        "student@example.com",
        "$argon2id$example-hash",
        "test-jti-123",
        1794390044,
    ) is False

    assert cursor.execute.call_count == 1


@pytest.mark.parametrize(
    "email,password_hash,jti,expiry",
    [
        ("not-an-email", "$argon2id$example-hash", "test-jti", 1794390044),
        ("", "$argon2id$example-hash", "test-jti", 1794390044),
        ("student@example.com", "", "test-jti", 1794390044),
        ("student@example.com", None, "test-jti", 1794390044),
        ("student@example.com", "$argon2id$example-hash", "", 1794390044),
        ("student@example.com", "$argon2id$example-hash", "test-jti", None),
    ],
)
def test_invalid_arguments_return_false(email, password_hash, jti, expiry):
    repository, connection, cursor = make_repository()

    assert repository.complete_password_setup(
        email, password_hash, jti, expiry
    ) is False

    cursor.execute.assert_not_called()
    connection.close.assert_not_called()


def test_database_failure_rolls_back_and_closes_connection():
    repository, connection, cursor = make_repository()

    cursor.execute.side_effect = RuntimeError("Database unavailable")

    with pytest.raises(RuntimeError, match="Database unavailable"):
        repository.complete_password_setup(
            "student@example.com",
            "$argon2id$example-hash",
            "test-jti-123",
            1794390044,
        )

    connection.__exit__.assert_called_once()
    assert connection.__exit__.call_args.args[0] is RuntimeError
    connection.close.assert_called_once()
