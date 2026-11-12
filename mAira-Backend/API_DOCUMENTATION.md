# MAIRA Phase 1 Backend — API Documentation

This document defines the complete API specification for the MAIRA Phase 1 Backend. All endpoints use JSON payloads, follow RFC 7807 error formats, enforce strict role-based access control, and utilize correlation tracking via `X-Request-ID`.

## Global Standards

- **Base URL**: `http://localhost:8000` (development) / `https://api.maira.institution.edu` (production)
- **API Version**: `v1`
- **Request Identification**: Every request can include an `X-Request-ID` header. If absent, the backend generates a UUID4 and echoes it in the response header `X-Request-ID`.
- **Security Headers**: All HTTP responses include `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
- **Authentication**: Bearer Token in `Authorization` header (`Authorization: Bearer <jwt_access_token>`).

---

## 1. System & Health Check Endpoints

### 1.1. Health Check
Checks application liveness, database connectivity to PostgreSQL schema `sch_con`, and connection pool availability.

- **Endpoint**: `GET /health`
- **Authentication**: None (Public)
- **Rate Limit**: 60 requests / minute

#### Response (200 OK)
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "database": {
    "status": "connected",
    "schema": "sch_con",
    "pool_status": {
      "pool_size": 10,
      "checked_in": 1,
      "checked_out": 0,
      "overflow": 0
    }
  },
  "timestamp": "2026-11-12T12:00:00.000000Z"
}
```

#### Error Response (503 Service Unavailable)
```json
{
  "status": "unhealthy",
  "version": "1.0.0",
  "environment": "production",
  "database": {
    "status": "disconnected",
    "error": "Connection refused"
  },
  "timestamp": "2026-11-12T12:00:00.000000Z"
}
```

---

## 2. Authentication & Onboarding Endpoints (`/api/v1/auth`)

### 2.1. Initiate Student Registration
Generates a 6-digit OTP for a pre-approved student email and registration number.

- **Endpoint**: `POST /api/v1/auth/register/initiate`
- **Authentication**: None (Public)
- **Rate Limit**: 5 requests / 15 minutes per IP

#### Request Body
```json
{
  "email": "student@institution.edu",
  "registration_number": "REG2026001"
}
```

#### Response (200 OK)
```json
{
  "message": "Verification OTP sent to your institutional email.",
  "masked_email": "s***t@institution.edu",
  "expires_in_seconds": 300
}
```

#### Error Responses
- `400 Bad Request`: Email/registration number mismatch, or account already activated (`password_hash IS NOT NULL`).
- `404 Not Found`: Student email is not in the approved database records.
- `429 Too Many Requests`: Rate limit exceeded for OTP generation.

---

### 2.2. Verify Registration OTP
Validates the 6-digit OTP against the stored SHA-256 hash. Upon success, returns a short-lived `registration_ticket`.

- **Endpoint**: `POST /api/v1/auth/register/verify-otp`
- **Authentication**: None (Public)
- **Rate Limit**: 5 attempts per OTP code

#### Request Body
```json
{
  "email": "student@institution.edu",
  "otp": "491823"
}
```

#### Response (200 OK)
```json
{
  "message": "OTP verified successfully. Proceed to set your password.",
  "registration_ticket": "reg_ticket_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in_seconds": 600
}
```

#### Error Responses
- `400 Bad Request`: Invalid OTP code (attempt counter incremented), OTP expired (> 5 minutes), or OTP already consumed.
- `429 Too Many Requests`: Maximum verification attempts (5) exceeded. OTP invalidated.

---

### 2.3. Set Account Password
Sets the initial password for the account using the signed `registration_ticket`.

- **Endpoint**: `POST /api/v1/auth/register/set-password`
- **Authentication**: Signed ticket token
- **Rate Limit**: 5 requests / 15 minutes

#### Request Body
```json
{
  "registration_ticket": "reg_ticket_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "SecurePassword123!"
}
```

#### Password Complexity Rules
- Minimum 8 characters, maximum 128 characters.
- Must contain at least one uppercase letter (`A-Z`).
- Must contain at least one lowercase letter (`a-z`).
- Must contain at least one digit (`0-9`).
- Must contain at least one special character (`!@#$%^&*()_+-=[]{}|;:,.<>?`).

#### Response (200 OK)
```json
{
  "message": "Account password set successfully. You can now log in."
}
```

#### Error Responses
- `400 Bad Request`: Password does not meet institutional complexity policy.
- `401 Unauthorized`: Registration ticket expired, invalid signature, or already consumed.

---

### 2.4. Account Login
Authenticates an approved institutional student or administrator, establishing a tracked session in `sch_con.tb_con_user_sessions`.

- **Endpoint**: `POST /api/v1/auth/login`
- **Authentication**: None (Public)
- **Rate Limit**: 5 requests / 15 minutes per IP

#### Request Body
```json
{
  "email": "student@institution.edu",
  "password": "SecurePassword123!",
  "role": "STUDENT"
}
```
*Note*: `role` must be either `STUDENT` or `ADMIN`.

#### Response (200 OK — MFA Disabled)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "a4f89b1c7e2d4f8a9e0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "user_id": 1,
    "email": "student@institution.edu",
    "role": "STUDENT",
    "status": "ACTIVE"
  }
}
```

#### Response (200 OK — MFA Enabled Challenge)
When `MFA_ENABLED=True`, login returns a challenge token and dispatches a 6-digit `LOGIN_MFA` code to the user's email:
```json
{
  "mfa_required": true,
  "mfa_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "MFA verification code sent to your email.",
  "expires_in_seconds": 300
}
```

#### Error Responses
- `401 Unauthorized`: Invalid credentials (constant-time verification prevents timing side-channels).
- `403 Forbidden`: Account is inactive or locked.

---

### 2.5. Verify Login MFA Code
Validates the MFA challenge token and the 6-digit email OTP, completing session establishment.

- **Endpoint**: `POST /api/v1/auth/mfa/verify`
- **Authentication**: None (Requires challenge `mfa_token`)
- **Rate Limit**: 5 attempts per challenge

#### Request Body
```json
{
  "mfa_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "code": "481920"
}
```

#### Response (200 OK)
Returns full session tokens:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "a4f89b1c7e2d4f8a9e0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "user_id": 1,
    "email": "student@institution.edu",
    "role": "STUDENT",
    "status": "ACTIVE"
  }
}
```

---

### 2.6. Rotate Refresh Token
Exchanges an active refresh token for a brand-new access token and rotated refresh token. Enforces automatic theft detection.

- **Endpoint**: `POST /api/v1/auth/refresh`
- **Authentication**: None (Refresh Token in body)
- **Rate Limit**: 30 requests / minute

#### Request Body
```json
{
  "refresh_token": "a4f89b1c7e2d4f8a9e0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b"
}
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3",
  "token_type": "Bearer",
  "expires_in": 900,
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "user": {
    "account_id": "11111111-1111-1111-1111-111111111111",
    "email": "student@institution.edu",
    "full_name": "John Doe",
    "role": "STUDENT",
    "account_type": "STUDENT"
  }
}
```

#### Error Responses
- `401 Unauthorized`: Token expired, malformed, or revoked. If a previously rotated token is re-submitted, all sessions for the user are immediately revoked (theft detection).

---

### 2.6. User Logout
Revokes the current session or all active sessions for the authenticated user.

- **Endpoint**: `POST /api/v1/auth/logout`
- **Authentication**: Bearer Token required
- **Rate Limit**: 30 requests / minute

#### Request Body (Optional)
```json
{
  "all_sessions": false
}
```

#### Response (200 OK)
```json
{
  "message": "Logged out successfully.",
  "sessions_revoked": 1
}
```

---

## 3. User Self-Service Endpoints (`/api/v1/users`)

### 3.1. Get Current User Profile
Retrieves authenticated profile information and roles.

- **Endpoint**: `GET /api/v1/users/me`
- **Authentication**: Bearer Token required (`STUDENT` or `ADMIN`)

#### Response (200 OK)
```json
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "email": "student@institution.edu",
  "full_name": "John Doe",
  "role": "STUDENT",
  "is_active": true,
  "created_at": "2026-09-01T08:00:00Z",
  "department": "Computer Science and Engineering",
  "year_of_study": 3
}
```

---

## 4. Administrator Endpoints (`/api/v1/admin/users`)

All admin endpoints require an active `ADMIN` Bearer token. Attempts by students return `403 Forbidden`.

### 4.1. Onboard Approved Student
Creates a pre-approved student record awaiting student-initiated registration.

- **Endpoint**: `POST /api/v1/admin/users/students`
- **Authentication**: Bearer Token required (`ADMIN` role)

#### Request Body
```json
{
  "email": "newstudent@institution.edu",
  "registration_number": "REG2026100",
  "full_name": "Alice Smith",
  "department": "Mechanical Engineering",
  "year_of_study": 1
}
```

#### Response (201 Created)
```json
{
  "user_id": "22222222-2222-2222-2222-222222222222",
  "email": "newstudent@institution.edu",
  "registration_number": "REG2026100",
  "full_name": "Alice Smith",
  "department": "Mechanical Engineering",
  "year_of_study": 1,
  "is_active": true,
  "is_registered": false,
  "created_at": "2026-11-12T12:00:00Z"
}
```

---

### 4.2. List Approved Students (Paginated)
- **Endpoint**: `GET /api/v1/admin/users/students?skip=0&limit=20&is_active=true`
- **Authentication**: Bearer Token required (`ADMIN` role)

#### Response (200 OK)
```json
{
  "items": [
    {
      "user_id": "22222222-2222-2222-2222-222222222222",
      "email": "newstudent@institution.edu",
      "registration_number": "REG2026100",
      "full_name": "Alice Smith",
      "department": "Mechanical Engineering",
      "year_of_study": 1,
      "is_active": true,
      "is_registered": false,
      "created_at": "2026-11-12T12:00:00Z"
    }
  ],
  "total": 19,
  "skip": 0,
  "limit": 20
}
```

---

### 4.3. Update Student Status
Activates or deactivates student access. Deactivation immediately invalidates all active sessions for that user.

- **Endpoint**: `PATCH /api/v1/admin/users/students/{user_id}/status`
- **Authentication**: Bearer Token required (`ADMIN` role)

#### Request Body
```json
{
  "is_active": false,
  "reason": "Administrative suspension pending semester clearance"
}
```

#### Response (200 OK)
```json
{
  "user_id": "22222222-2222-2222-2222-222222222222",
  "is_active": false,
  "message": "User status updated successfully. Active sessions revoked."
}
```

---

### 4.4. Institutional Analytics
Provides high-level metrics for administrative dashboards.

- **Endpoint**: `GET /api/v1/admin/users/analytics`
- **Authentication**: Bearer Token required (`ADMIN` role)

#### Response (200 OK)
```json
{
  "total_students": 19,
  "active_students": 18,
  "registered_students": 12,
  "total_sessions": 45,
  "total_conversations": 64,
  "total_messages": 312
}
```

---

## 5. Conversational AI & Chat Endpoints (`/api/v1/chat`)

Accessible only to authenticated institutional users (`STUDENT`). Administrators attempting to initiate chats receive `403 Forbidden`.

### 5.1. Create Chat Session
Initializes an isolated conversational thread.

- **Endpoint**: `POST /api/v1/chat/sessions`
- **Authentication**: Bearer Token required (`STUDENT` role)

#### Request Body
```json
{
  "title": "Data Structures Study Assistant",
  "metadata": {
    "subject": "CS301",
    "topic": "Binary Search Trees"
  }
}
```

#### Response (201 Created)
```json
{
  "session_id": "33333333-3333-3333-3333-333333333333",
  "title": "Data Structures Study Assistant",
  "created_at": "2026-11-12T12:10:00Z",
  "updated_at": "2026-11-12T12:10:00Z",
  "message_count": 0,
  "is_active": true
}
```

---

### 5.2. List Chat Sessions
Retrieves conversational threads owned by the authenticated student.

- **Endpoint**: `GET /api/v1/chat/sessions?skip=0&limit=20`
- **Authentication**: Bearer Token required (`STUDENT` role)

#### Response (200 OK)
```json
[
  {
    "session_id": "33333333-3333-3333-3333-333333333333",
    "title": "Data Structures Study Assistant",
    "created_at": "2026-11-12T12:10:00Z",
    "updated_at": "2026-11-12T12:10:00Z",
    "message_count": 2,
    "is_active": true
  }
]
```

---

### 5.3. Send Message & Receive AI Response
Appends the student prompt to the session, queries the Gen AI microservice via `POST /api/v1/generate`, and persists the assistant reply.

- **Endpoint**: `POST /api/v1/chat/sessions/{session_id}/messages`
- **Authentication**: Bearer Token required (`STUDENT` role)
- **Rate Limit**: 20 messages / minute

#### Request Body
```json
{
  "content": "Explain the time complexity of AVL tree insertions with rotations."
}
```

#### Response (200 OK)
```json
{
  "user_message": {
    "message_id": "44444444-4444-4444-4444-444444444444",
    "session_id": "33333333-3333-3333-3333-333333333333",
    "sender_role": "USER",
    "content": "Explain the time complexity of AVL tree insertions with rotations.",
    "created_at": "2026-11-12T12:11:00Z"
  },
  "assistant_message": {
    "message_id": "55555555-5555-5555-5555-555555555555",
    "session_id": "33333333-3333-3333-3333-333333333333",
    "sender_role": "ASSISTANT",
    "content": "AVL tree insertion has a time complexity of O(log n). Finding the insertion location takes O(log n) time, and rebalancing via single or double rotations takes O(1) time.",
    "created_at": "2026-11-12T12:11:02Z",
    "reply_to_message_id": "44444444-4444-4444-4444-444444444444"
  },
  "correlation_id": "req_8f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
}
```

#### Error Responses
- `403 Forbidden`: Attempting to send messages to another student's chat session (IDOR prevention).
- `502 Bad Gateway`: External Gen AI service unavailable or returned unexpected error code.
- `504 Gateway Timeout`: Gen AI inference exceeded read timeout (30 seconds).

---

### 5.4. Soft Delete Chat Session
Marks a conversation as deleted without purging institutional audit history.

- **Endpoint**: `DELETE /api/v1/chat/sessions/{session_id}`
- **Authentication**: Bearer Token required (`STUDENT` role)

#### Response (200 OK)
```json
{
  "message": "Chat session deleted successfully."
}
```

---

## 6. RFC 7807 Error Response Specification

All error responses return a standardized JSON schema:

```json
{
  "error": {
    "code": "ACCOUNT_DEACTIVATED",
    "message": "Account has been deactivated. Please contact an administrator.",
    "request_id": "req_1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "timestamp": "2026-11-12T12:15:00Z"
  }
}
```

### Standard Error Codes
| HTTP Status | Error Code | Description |
|---|---|---|
| `400` | `INVALID_INPUT` / `VALIDATION_ERROR` | Schema validation error or missing required field |
| `401` | `AUTHENTICATION_REQUIRED` / `INVALID_TOKEN` | Bearer token missing, expired, or tampered |
| `401` | `SESSION_REVOKED` | Session revoked or refresh token reuse detected |
| `403` | `FORBIDDEN` / `PERMISSION_DENIED` | Insufficient RBAC permissions or IDOR violation |
| `403` | `ACCOUNT_INACTIVE` | Account deactivated by administrative action |
| `404` | `NOT_FOUND` | Resource (user, chat, message) does not exist |
| `409` | `CONFLICT` | Resource already exists (e.g. duplicate email/registration number) |
| `429` | `RATE_LIMIT_EXCEEDED` | Request throttled by sliding-window rate limiter |
| `502` | `GENAI_SERVICE_UNAVAILABLE` | External Gen AI microservice connection failure |
| `504` | `GENAI_SERVICE_TIMEOUT` | Gen AI inference exceeded 30s deadline |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled exception (sanitized, stack trace suppressed) |
