"""PostgreSQL repository for secure, one-time password setup."""

from contextlib import closing


class _PasswordSetupRejected(Exception):
    pass


class PostgresUserPasswordRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def complete_password_setup(
        self,
        email: str,
        password_hash: str,
        jti: str,
        expires_at: float,
    ) -> bool:
        if (
            not isinstance(email, str)
            or not email.strip()
            or "@" not in email
            or not isinstance(password_hash, str)
            or not password_hash
            or not isinstance(jti, str)
            or not jti.strip()
            or isinstance(expires_at, bool)
            or not isinstance(expires_at, (int, float))
        ):
            return False

        try:
            with closing(self.connection_factory()) as connection:
                with connection:
                    with connection.cursor() as cursor:

                        cursor.execute(
                            """
                            INSERT INTO sch_con.tb_con_registration_token_usage
                                (jti, email, expires_at)
                            SELECT %s, %s, to_timestamp(%s)
                            WHERE to_timestamp(%s) > CURRENT_TIMESTAMP
                            ON CONFLICT (jti) DO NOTHING
                            RETURNING jti
                            """,
                            (jti, email.strip(), expires_at, expires_at),
                        )

                        if cursor.fetchone() is None:
                            raise _PasswordSetupRejected()

                        cursor.execute(
                            """
                            UPDATE sch_con.tb_con_user
                            SET password_hash = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE LOWER(email) = LOWER(%s)
                              AND status = 'ACTIVE'
                              AND password_hash IS NULL
                            """,
                            (password_hash, email.strip()),
                        )

                        if cursor.rowcount != 1:
                            raise _PasswordSetupRejected()

            return True

        except _PasswordSetupRejected:
            return False
