# Group 4 – Session Management and JWT Issuance

## 1. Overview

This module handles session management and JSON Web Token (JWT) operations for the MAira backend.

Its main responsibilities are:

- Generate JWT access tokens.
- Validate access tokens.
- Generate and verify refresh tokens.
- Rotate refresh tokens securely.
- Revoke refresh tokens and sessions.
- Validate JWT configuration.

Implementation file:

`modules/m_auth/m_auth_sm_session.py`

Test file:

`tests/test_session.py`

## 2. Access Token Management

### Access Token Generation

Function: `create_access_token()`

Generates a signed JWT access token for an authenticated user.

The token contains:

- `sub`: User ID.
- `sid`: Session ID.
- `jti`: Unique token ID.
- `iat`: Token creation time.
- `exp`: Token expiration time.
- `iss`: Token issuer.
- `aud`: Intended audience.
- `type`: Token type (`access`).
- `email`: Optional user email.
- `role`: Optional user role.

The default access-token lifetime is 15 minutes.

### Access Token Validation

Function: `verify_access_token()`

Validates:

- JWT signature.
- Token expiration.
- Issuer and audience.
- Required claims.
- Access-token type.
- Session revocation status.

Invalid tokens are rejected.

## 3. Refresh Token Management

### Refresh Token Generation

Function: `create_refresh_token()`

Generates a cryptographically secure random refresh token.

### Refresh Token Hashing

Function: `hash_refresh_token()`

Uses SHA-256 to generate a hash of the refresh token.

Only the hash is stored in the current session registry.

### Refresh Token Verification

Function: `verify_refresh_token()`

Compares the supplied refresh token against its stored hash using constant-time comparison.

### Refresh Token Rotation

Function: `refresh_session()`

The refresh workflow:

1. Receives the existing refresh token.
2. Calculates its hash.
3. Checks whether the token exists and is valid.
4. Checks expiration and revocation status.
5. Revokes the old refresh token.
6. Generates a new access token and refresh token.

The old refresh token cannot be reused after successful rotation.

The default refresh-token lifetime is seven days.

## 4. Session Revocation and Logout

The module provides:

- `revoke_refresh_token()`: Revokes an individual refresh token.
- `revoke_session()`: Revokes a session and its associated refresh tokens.
- `logout()`: Performs session revocation.

Revoked sessions are rejected during access-token validation.

## 5. Configuration

Configuration is loaded from environment variables.

| Variable | Default |
|---|---|
| JWT_ALGORITHM | HS256 |
| JWT_ISSUER | maira-backend |
| JWT_AUDIENCE | maira-api |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 15 |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 |
| JWT_SECRET_KEY | Must be configured |

The JWT secret helper validates that the configured secret contains at least 32 bytes.

A real secret must be kept in the local `.env` file and must never be committed to GitHub.

## 6. Current Storage Implementation

The current implementation uses temporary in-memory storage:

- `_REFRESH_SESSIONS`
- `_REVOKED_SESSIONS`

This allows the session functionality to be tested independently of the database.

Important limitations:

- Session information is lost when the application restarts.
- Storage is not shared between multiple application workers.
- Persistent refresh-token storage is not implemented.
- Database-backed revocation and atomic token rotation are pending.

These in-memory structures are temporary and must be replaced or integrated with the approved database implementation before production deployment.

## 7. Testing

Test file:

`tests/test_session.py`

The current test suite covers:

- Valid and invalid access tokens.
- Expired access tokens.
- Tampered JWTs.
- Invalid issuer and audience.
- Missing JWT claims.
- JWT secret validation.
- Refresh-token hashing and verification.
- Refresh-token expiration.
- Refresh-token rotation and reuse rejection.
- Invalid inputs.
- Session revocation.
- Logout functionality.

Latest test results:

- Total tests: 32
- Passed: 32
- Failed: 0
- Statement coverage: 100%

These results represent the current local test run.

## 8. Pending Integration Work

The following tasks require external dependencies or team coordination.

### Database Team

- Persistent session storage.
- Refresh-token hash storage.
- Token expiration and revocation persistence.
- Database-backed session lookup.
- Atomic refresh-token rotation.

### Authentication and Other Groups

- Login and onboarding integration.
- MFA verification integration.
- User identity and account-status integration.
- Role-based access integration.
- Security middleware and audit logging.
- API route integration and end-to-end testing.

The API endpoints identified in the project requirements are:

- `POST /api/v1/auth/session`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

Their implementation and integration remain pending the agreed API contracts and team coordination.

## 9. Current Status

The standalone JWT session-management module has been implemented and tested.

It is not yet a complete production-ready authentication system because persistent storage and application-level integration remain pending.

