"""Password setup orchestration for MAira."""

from typing import Protocol
from modules.m_auth.m_auth_pw_security import hash_password


class RegistrationTokenService(Protocol):
    def verify_registration_token(self, token: str) -> dict | None:
        ...


class UserPasswordRepository(Protocol):
    def complete_password_setup(
        self, email: str, password_hash: str, jti: str, expires_at: float
    ) -> bool:
        ...


class InvalidRegistrationToken(Exception):
    pass


class PasswordSetupNotAllowed(Exception):
    pass


class PasswordSetupService:
    def __init__(self, token_service, user_repository):
        self.token_service = token_service
        self.user_repository = user_repository

    def setup_password(self, token: str, password: str) -> None:
        if not isinstance(token, str) or not token.strip():
            raise InvalidRegistrationToken("Invalid or expired registration token.")

        if not isinstance(password, str) or not password:
            raise ValueError("Password cannot be empty.")

        claims = self.token_service.verify_registration_token(token)

        if not claims:
            raise InvalidRegistrationToken("Invalid or expired registration token.")

        password_hash = hash_password(password)

        completed = self.user_repository.complete_password_setup(
            claims["email"],
            password_hash,
            claims["jti"],
            claims["exp"],
        )

        if not completed:
            raise PasswordSetupNotAllowed(
                "Password setup is not allowed for this account."
            )
