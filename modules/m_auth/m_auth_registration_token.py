"""Verify Group 3 temporary registration tokens."""

import base64
import hashlib
import hmac
import json
import os
import time


class RegistrationTokenVerifier:
    def __init__(self):
        self.secret_key = os.getenv("MAIRA_AUTH_SECRET_KEY")
        if not self.secret_key:
            raise RuntimeError("MAIRA_AUTH_SECRET_KEY is not configured.")

    def verify_registration_token(self, token: str) -> dict | None:
        try:
            if not isinstance(token, str) or len(token) > 4096:
                return None

            payload_part, signature = token.split(".")

            expected = hmac.new(
                self.secret_key.encode("utf-8"),
                payload_part.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                return None

            padded = payload_part + "=" * (-len(payload_part) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(padded).decode("utf-8")
            )

            if not isinstance(payload, dict):
                return None

            email = payload.get("email")
            jti = payload.get("jti")
            expiry = payload.get("exp")

            if (
                payload.get("flow") != "registration"
                or payload.get("stage") != "step_3_password_setup"
                or not isinstance(email, str)
                or not email.strip()
                or payload.get("sub") != email
                or not isinstance(jti, str)
                or not jti.strip()
                or isinstance(expiry, bool)
                or not isinstance(expiry, (int, float))
                or time.time() >= expiry
            ):
                return None

            return {
                "email": email.strip(),
                "jti": jti,
                "exp": expiry,
            }

        except (ValueError, TypeError, KeyError, UnicodeDecodeError):
            return None
