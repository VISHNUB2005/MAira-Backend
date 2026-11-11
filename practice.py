"""Quick manual try-out of the Group 7 email service.  Run:  python practice.py

Uses whatever EMAIL_PROVIDER your .env / terminal sets (default: console).
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()                      # your .env wins over the demo defaults below
# DEMO ONLY: fills gaps so this script runs with no .env. Never do this in the real application.
os.environ.setdefault("DATABASE_URL", "sqlite:///practice.db")
os.environ.setdefault("JWT_SECRET_KEY", "practice-key-" + "x" * 40)

from xsc_lib.xsc_lib_app.xsc_lib_a_config import settings
from xsc_lib.xsc_lib_app.xsc_lib_a_email import (
    EmailDeliveryError, EmailPurpose, EmailValidationError, email_service,
)

TO = "alice@organization.com"      # change to an inbox you own when using a real provider

print("Provider:", settings.email_provider)
print("OTP expires in:", settings.otp_expiry_minutes, "minutes")


async def main():
    try:
        print(await email_service.send_otp(TO, "123456", EmailPurpose.REGISTRATION))
        print(await email_service.send_otp(TO, "654321", EmailPurpose.LOGIN))
    except EmailValidationError as exc:
        print("Rejected input:", exc)
    except EmailDeliveryError as exc:
        print(f"Email failed (code={exc.code}, permanent={exc.permanent}). The API would return 503 here.")


asyncio.run(main())
