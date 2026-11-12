# MAira Backend — Group 2: Password Security & Setup

## 1. Purpose

Allow verified users to create passwords securely without storing plaintext passwords.

## 2. Implementation

Group 2 implementation files:

- `modules/m_auth/m_auth_pw_security.py`
- `modules/m_auth/m_auth_password_setup.py`
- `modules/m_auth/m_auth_password_routes.py`
- `modules/m_auth/m_auth_password_repository.py`
- `modules/m_auth/m_auth_registration_token.py`
- `migrations/001_registration_token_usage.sql`

## 3. Password Security

- Uses `pwdlib` with its recommended Argon2id password hasher.
- Generates unique salts through the password-hashing library.
- Supports password verification.
- Rejects empty passwords and malformed hashes.
- Never returns password hashes through the API.
- Password setup is restricted to eligible account states.

## 4. API Contract

Endpoint: `POST /api/v1/auth/password/setup`

Request:

    {
      "registration_token": "<short-lived-registration-token>",
      "password": "<new-password>"
    }

Success response (HTTP 200):

    {
      "message": "Password setup completed successfully."
    }

Error responses:

- HTTP 400: Invalid or expired registration token.
- HTTP 409: Password setup not allowed for this account.
- HTTP 422: Invalid request body.
- HTTP 503: Password setup service is not configured.

The local API implementation is available. Final shared API contract approval remains subject to integration-team review.

## 5. Registration Token Security

- Validates the Group 3 registration token format.
- Uses the shared `MAIRA_AUTH_SECRET_KEY` configuration.
- Validates token signature, registration flow, password-setup stage, email, JTI and expiry.
- Rejects expired or invalid tokens.
- Uses a persistent PostgreSQL JTI usage table to prevent token replay.
- Database insertion and password persistence execute within one transaction.

Migration:
`migrations/001_registration_token_usage.sql`

The migration creates:
`sch_con.tb_con_registration_token_usage`

Apply the migration before using the PostgreSQL password repository.

## 6. Database and Account Eligibility

User table:
`sch_con.tb_con_user`

Relevant fields:

- `email`
- `user_type`
- `password_hash`
- `status`
- `updated_at`

Password setup currently requires:

- Account status is `ACTIVE`.
- Existing `password_hash` is `NULL`.
- Registration token JTI has not already been consumed.

The JTI insertion and password update share a transaction. If the account update fails, the JTI insertion is rolled back.

Production database configuration must use a dedicated application database role with least-privilege permissions. Local development currently uses the PostgreSQL `postgres` role.

## 7. Integration Dependencies

### Group 3 — OTP and Verification

- Registration-token format compatibility implemented and locally tested.
- Shared secret configuration uses `MAIRA_AUTH_SECRET_KEY`.
- Persistent JTI replay protection implemented.
- Final shared token-consumption contract requires coordination.

### Group 5 — User Identity and Profile Data

- Local implementation uses the existing user table and password-hash field.
- Account status must be `ACTIVE` for password setup.
- Final account-status transition contract requires confirmation.

### Other coordination

- Group 1: eligible registration flow.
- Group 4: login/session integration.
- Group 7: secure configuration and secrets.
- Group 9: integration testing.

## 8. Security and Reliability

- No plaintext or reversibly encrypted password storage.
- No direct password/token/hash logging found in the scanned Group 2 Python files.
- Password request limit: 1,024 characters.
- Registration token limit: 4,096 characters.
- Missing shared secret causes configuration failure rather than use of a fallback secret.
- Database operations use transaction handling.
- Expired tokens are independently rejected by the database repository.
- Production database permissions must follow least-privilege principles.

## 9. Test and Verification Results

Latest local automated test result:

**38 passed, 1 warning.**

The non-blocking warning concerns Starlette's deprecated use of `httpx` with its test client.

Real PostgreSQL integration checks completed:

- Successful active-account password setup.
- JTI recorded after successful setup.
- Replayed token rejected.
- Inactive account rejected.
- JTI insertion rolled back for inactive account.
- Expired token rejected by the database.
- Expired JTI not recorded.
- Temporary integration-test data cleaned up.

## 10. Remaining Work

1. Confirm account-status transition contract with Group 5.
2. Confirm login/session integration with Groups 3 and 4.
3. Review production database role and permissions.
4. Finalize shared API and database contracts.
5. Complete RMP and handover evidence.
6. Obtain company permission before submitting code.

## 11. Git Workflow

Working branch:

`feature/group-2-password-security`

No commit or push should be performed until company permission is received.
