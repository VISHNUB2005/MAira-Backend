"""
run_demo.py  -  see the Group 7 email service work end to end.

    python run_demo.py

What happens:
  1. You type an email address and choose registration or login.
  2. A 6-digit code is created and sent with the Group 7 email service
     (console mode prints it in this terminal; file mode saves outbox/latest.html).
  3. You type the code back and it is checked: expiry, attempts and single use.

DEMO ONLY: the code store (demo/demo_otp_store.py) stands in for Group 3,
which owns real OTP storage and verification.
"""
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()                      # your .env wins over the demo defaults below
# DEMO ONLY: fills gaps so this script runs with no .env. Never do this in the real application.
os.environ.setdefault("DATABASE_URL", "sqlite:///demo.db")
os.environ.setdefault("JWT_SECRET_KEY", "demo-key-" + "x" * 40)

try:
    from xsc_lib.xsc_lib_app.xsc_lib_a_config import settings
except Exception as exc:                      # e.g. unsafe values in your .env
    print("Configuration problem:\n", exc)
    sys.exit(1)

from demo.demo_otp_store import DemoOtpStore
from xsc_lib.xsc_lib_app.xsc_lib_a_email import (
    EmailDeliveryError,
    EmailValidationError,
    send_login_otp,
    send_registration_otp,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _where_to_look(email: str) -> str:
    provider = settings.email_provider
    if provider == "console":
        return "The email, including your code, was printed in this terminal just above."
    if provider == "file":
        return f"Open this file in your browser to see the email:\n  {(Path(settings.email_outbox_dir) / 'latest.html').resolve()}"
    if provider == "mock":
        return "Mock mode: the email was stored in memory."
    return f"Check the inbox of {email} (and the spam folder)."


def run(ask=input, say=print, store=None) -> bool:
    """Returns True if the code was verified."""
    store = store or DemoOtpStore(
        length=settings.otp_length,
        expiry_seconds=settings.otp_expiry_minutes * 60,
        max_attempts=settings.otp_max_attempts,
    )
    say(f"Provider: {settings.email_provider}   |   code expires in {settings.otp_expiry_minutes} minutes\n")

    email = ask("Email address [alice@organization.com]: ").strip() or "alice@organization.com"
    if not EMAIL_RE.match(email):
        say("That does not look like an email address.")
        return False
    flow = ask("Flow  1 = registration   2 = login  [1]: ").strip() or "1"
    send = send_login_otp if flow == "2" else send_registration_otp

    try:
        otp = store.issue(email)
        result = asyncio.run(send(email, otp))
    except EmailDeliveryError:
        say("Could not send the email (the API would return 503 here).")
        return False
    except EmailValidationError as exc:
        say(f"Rejected input: {exc}")
        return False

    say(f"\nEmail accepted by provider '{result.provider}' (accepted for delivery, not confirmed delivered).")
    say(_where_to_look(email) + "\n")

    for attempt in range(1, settings.otp_max_attempts + 1):
        code = ask("Type the verification code: ").strip()
        outcome = store.verify(email, code)
        if outcome == "ok":
            say("VERIFIED. The code was correct and has now been used up.")
            return True
        messages = {
            "wrong": f"Incorrect code ({settings.otp_max_attempts - attempt} tries left).",
            "expired": "The code has expired. Run the demo again.",
            "locked": "Too many wrong attempts. Run the demo again.",
            "none": "No code is active for this email.",
        }
        say(messages[outcome])
        if outcome != "wrong":
            return False
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    try:
        sys.exit(0 if run() else 1)
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(1)
