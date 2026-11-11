"""
demo_otp_store.py  (DEMO ONLY - the real version is Group 3's job)
In-memory OTP store: 5-minute expiry, max attempts, single use, resend cooldown.
Codes are stored hashed, never in plain text.
"""
import hashlib
import hmac
import secrets
import time
from typing import Callable, Dict

class DemoOtpStore:
    def __init__(self, length=6, expiry_seconds=300, max_attempts=5, cooldown_seconds=30,
                 clock: Callable[[], float] = time.time):
        self.length, self.expiry, self.max_attempts = length, expiry_seconds, max_attempts
        self.cooldown, self.clock = cooldown_seconds, clock
        self._items: Dict[str, dict] = {}

    @staticmethod
    def _hash(otp: str) -> str:
        return hashlib.sha256(otp.encode()).hexdigest()

    def issue(self, email: str) -> str:
        """Returns the new OTP. Raises ValueError('cooldown') if asked again too soon."""
        email, now = email.strip().lower(), self.clock()
        old = self._items.get(email)
        if old and now - old["issued"] < self.cooldown:
            raise ValueError("cooldown")
        otp = "".join(secrets.choice("0123456789") for _ in range(self.length))
        self._items[email] = {"hash": self._hash(otp), "issued": now,
                              "expires": now + self.expiry, "attempts": 0}
        return otp

    def verify(self, email: str, otp: str) -> str:
        """Returns 'ok', 'wrong', 'expired', 'locked' or 'none'."""
        email = email.strip().lower()
        item = self._items.get(email)
        if not item:
            return "none"
        if self.clock() > item["expires"]:
            del self._items[email]
            return "expired"
        if item["attempts"] >= self.max_attempts:
            del self._items[email]
            return "locked"
        item["attempts"] += 1
        if hmac.compare_digest(item["hash"], self._hash(otp.strip())):
            del self._items[email]          # single use
            return "ok"
        return "wrong"
