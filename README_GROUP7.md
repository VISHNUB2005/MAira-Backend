# MAira Backend: Group 7 (Email dispatch & secrets management)

Files: `xsc_lib/xsc_lib_app/xsc_lib_a_email.py`, `xsc_lib_a_secrets.py`, `xsc_lib_a_config.py`
Review response and evidence checklist: `G7_REVIEW_RESPONSE.md`

## What it does (and does not do)
- Delivers OTP emails for registration (Flow A) and login MFA (Flow B), and loads settings/secrets in one place.
- **Does not** generate, store, expire or verify OTPs (Group 3), authenticate callers, rate-limit, or enforce the
  institutional-domain policy (Group 1 / the API layer). Those are upstream responsibilities.

## Service contract (for Groups 1 and 3)
```python
from xsc_lib.xsc_lib_app.xsc_lib_a_email import (
    email_service, EmailPurpose, EmailDeliveryError, EmailValidationError,
)

try:
    result = await email_service.send_otp(to_email, otp, EmailPurpose.LOGIN)   # or EmailPurpose.REGISTRATION
except EmailValidationError:   # bad address / OTP format / purpose      -> 422 (caller bug)
    ...
except EmailDeliveryError as e:  # e.code (sanitized), e.permanent      -> 503 "try again"
    ...
```
`send_registration_otp(to, otp)` and `send_login_otp(to, otp)` call the same code.

`SendResult`: `accepted` (SMTP server accepted it), `provider`, `message_id` (our own Message-ID header),
`delivery_confirmed` (always False: no provider webhooks yet), `simulated` (True for console/file/mock).
**`accepted` is not proof the email reached the inbox.**

`EmailDeliveryError.code`: `AUTH_FAILED`, `RECIPIENT_REFUSED`, `SENDER_REFUSED`, `PERMANENT_REJECTION`,
`TEMPORARY_REJECTION`, `TLS_FAILED`, `SERVER_UNSUPPORTED`, `TIMEOUT`, `CONNECTION_FAILED`, `UNKNOWN`.
Messages never contain OTPs, addresses, credentials or server text.

## Provider support matrix
| EMAIL_PROVIDER | Status | Use |
|---|---|---|
| `smtp` | implemented | Real delivery. Verified TLS. **Still needs one test against the approved SMTP sandbox.** |
| `mock` | implemented | Automated tests (in-memory outbox, thread-safe). Development/test only. |
| `console` | dev helper | Prints the email **including the OTP**. Development/test only. |
| `file` | dev helper | Saves `outbox/latest.html`. Development/test only. |
| `ses`, `sendgrid` | **not supported** | Rejected at startup with a clear message. |

## Configuration
Copy `.env.example` to `.env` (never commit it). There are **no default credentials and no default JWT key**.
Startup stops with a list of problems (never secret values) if anything is missing or invalid:
host/username/password/sender (reported separately as "not set" vs "set but empty"), port 1-65535, timeout 1-120,
provider, environment (`development|test|staging|production`), TLS mode, JWT key length/placeholder, OTP bounds.
Console/file/mock and `EMAIL_TLS_MODE=none` are rejected in staging and production.
Names: `EMAIL_HOST/PORT/USERNAME/PASSWORD` (old `SMTP_*` names still work as a fallback).

## Secrets: precedence
1. environment variable `NAME` (including `.env`) 2. file named by `NAME_FILE` 3. `/run/secrets/<name_lowercase>`
4. AWS Secrets Manager (`AWS_SECRETS_NAME`). Blank values count as not provided. A missing `NAME_FILE` target or an
unreadable file stops the app with a clear message. In production use the company secret manager, not a `.env` file.
Secrets are excluded from `repr(settings)` and never logged.

## SMTP behaviour
- `starttls` (default) or `ssl`: certificate **and hostname** verified (`ssl.create_default_context()`); if the server
  does not offer STARTTLS or the certificate is untrusted, sending fails closed and credentials are never sent.
- Timeout `EMAIL_TIMEOUT_SECONDS` (default 15). Up to 3 attempts with exponential backoff + jitter (cap 8s).
  Permanent failures (bad credentials, 5xx, refused recipient, TLS failure) are not retried.
- A retry after a timeout can in rare cases send the same OTP twice; callers must not assume exactly-once delivery.
- Logs: masked address, error code and exception *type* only. Console/file/demo modes print the OTP on purpose
  (development only).

## Run it
See `START_HERE.txt`. Tests: `python -m pytest -v`. Demo (no email account needed): `python run_demo.py`.

## Known limitations
- Real SMTP delivery is not yet proven against the approved sandbox; TLS is proven against a local test server.
- No delivery confirmation (needs provider webhooks). No SES/SendGrid. No per-address rate limit here.
- Without the `email-validator` package a strict built-in validator is used (ASCII addresses only).
