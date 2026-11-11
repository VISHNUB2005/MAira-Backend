"""
Runs before any test file is imported. Makes the tests independent of your real
.env file and of any EMAIL_*/SMTP_* variables set in your terminal.
"""
import os

import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False      # never read a real .env in tests

for _name in (
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USERNAME", "EMAIL_PASSWORD",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_USE_TLS",
    "SENDGRID_API_KEY", "EMAIL_OUTBOX_DIR", "AWS_SECRETS_NAME", "EMAIL_FROM_ADDRESS", "EMAIL_FROM_NAME",
    "EMAIL_TLS_MODE", "EMAIL_TIMEOUT_SECONDS", "EMAIL_HOST_FILE", "EMAIL_PASSWORD_FILE", "EMAIL_USERNAME_FILE",
):
    os.environ.pop(_name, None)

os.environ["ENVIRONMENT"] = "development"
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["JWT_SECRET_KEY"] = "a" * 40
