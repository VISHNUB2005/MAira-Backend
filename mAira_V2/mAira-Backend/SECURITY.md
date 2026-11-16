# MAIRA Phase 1 Backend — Security Architecture & Hardening Guide

This document provides a comprehensive security assessment, threat model, defense-in-depth specification, and vulnerability analysis for the MAIRA Phase 1 Backend.

---

## 1. Threat Model & Institutional Risk Profile

The MAIRA Phase 1 Backend serves an educational institution, storing student identifiers, conversational records, and administrative controls. The system was designed to withstand the following primary threat vectors:

1. **Credential Stuffing & Brute Force**: Automated dictionary attacks on student login and registration endpoints.
2. **Timing Attacks (Side-Channel Enumeration)**: Discerning valid student emails by measuring server response times during password verification.
3. **Session Hijacking & Token Theft**: Interception or unauthorized replay of refresh tokens across distributed clients.
4. **Insecure Direct Object Reference (IDOR)**: Malicious students querying or modifying conversational histories of peers.
5. **Privilege Escalation**: Students invoking administrative endpoints to alter statuses or onboard unauthorized accounts.
6. **Data Leakage in Logs & Error Traces**: Accidental output of cleartext passwords, OTPs, or API keys in application log streams or RFC 7807 error responses.
7. **Supply Chain & Dependency Vulnerabilities**: Exploits targeting third-party Python packages.

---

## 2. Defense-in-Depth Security Controls

```
+─────────────────────────────────────────────────────────────────────────────+
| 1. EDGE & TRANSPORT LAYER                                                   |
|    - TLS 1.3 Termination (HTTPS only)                                       |
|    - Strict-Transport-Security: max-age=31536000; includeSubDomains; preload |
|    - Content-Security-Policy: default-src 'self'; frame-ancestors 'none'    |
|    - X-Frame-Options: DENY                                                  |
|    - X-Content-Type-Options: nosniff                                        |
|    - CORS: Strict explicit origin allowlist; rejects wildcard ('*') with    |
|      credentials                                                            |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼
+─────────────────────────────────────────────────────────────────────────────+
| 2. TRAFFIC REGULATION & RATE LIMITING (app/security/rate_limiter.py)         |
|    - Sliding-window in-memory limiter tracking client IP + action           |
|    - Login: 5 requests / 15 minutes                                         |
|    - OTP Verification: 5 attempts per generated OTP code                    |
|    - Chat Messages: 20 messages / minute                                    |
|    - RFC 7807 429 Too Many Requests response with Retry-After header         |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼
+─────────────────────────────────────────────────────────────────────────────+
| 3. AUTHENTICATION & SESSION SECURITY (app/core/security.py)                 |
|    - Passwords: Bcrypt (12 salt rounds); NULL-hash dummy comparison         |
|    - OTPs: Cryptographic random 6-digits; SHA-256(OTP:email) salted digest |
|    - Access Tokens: HS256 JWT, 15-minute lifespan, session revocation check |
|    - Refresh Tokens: 64-byte opaque random; SHA-256 hashed in database      |
|    - Theft Detection: Replay of revoked refresh token revokes all user      |
|      sessions and triggers critical audit alarm                             |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼
+─────────────────────────────────────────────────────────────────────────────+
| 4. AUTHORIZATION & ACCESS CONTROL (app/security/permissions.py)             |
|    - Role-Based Access Control (RBAC): ADMIN, STUDENT, FACULTY              |
|    - Zero-Trust Endpoint Guards (require_role, require_permission)          |
|    - Anti-IDOR Scoping: All chat/user queries require compound matching:    |
|      WHERE resource_id = :id AND user_id = :auth_user_id                    |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼
+─────────────────────────────────────────────────────────────────────────────+
| 5. SECRETS & DATA HYGIENE (app/security/secrets.py, app/utils/redaction.py) |
|    - Priority Secrets Hierarchy: ENV -> Docker Secret -> Disk File          |
|    - Secret Masking: mask_secret() outputs 'secr***' in logs/errors         |
|    - Sensitive Field Sanitizer: Recursively scrubs 'password', 'token',     |
|      'otp', 'secret', 'authorization' keys from all JSON log dictionaries   |
|    - Generic Error Responses: Internal 500 errors suppress stack traces     |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼
+─────────────────────────────────────────────────────────────────────────────+
| 6. AUDIT & FORENSICS (app/security/audit_logger.py)                         |
|    - sch_con.tb_con_audit_log records actor_id, IP, action, and timestamp   |
|    - Events: LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, REFRESH_ROTATED,          |
|      REFRESH_TOKEN_REUSE_DETECTED, PASSWORD_SET, STUDENT_STATUS_CHANGED     |
|    - Tamper-resistant append-only architecture                              |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Cryptographic Implementation Details

### 3.1. Password Hashing & Timing Attack Defense
```python
# app/core/security.py
DUMMY_HASH = bcrypt.hashpw(b"constant_timing_dummy_password", bcrypt.gensalt(12)).decode()

def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        # Prevents account enumeration by executing identical bcrypt work factor
        bcrypt.checkpw(plain_password.encode("utf-8"), DUMMY_HASH.encode("utf-8"))
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

### 3.2. Salted OTP Storage
```python
def hash_otp(otp: str, email: str) -> str:
    # Binds OTP to email to prevent cross-account reuse
    payload = f"{otp}:{email.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def verify_otp_hash(plain_otp: str, email: str, stored_hash: str) -> bool:
    candidate_hash = hash_otp(plain_otp, email)
    # Constant-time comparison prevents timing analysis
    return secrets.compare_digest(candidate_hash, stored_hash)
```

### 3.3. Refresh Token Hashing & Theft Detection
```python
def hash_refresh_token(token: str) -> str:
    # Stored in sch_con.tb_con_user_sessions.refresh_token_hash
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```
When a revoked token hash is presented, the system triggers `AuthService.revoke_all_sessions(account_id)`, terminating any active sessions the attacker or user may hold.

---

## 4. Security Audit & Automated Vulnerability Scanning

### 4.1. Bandit Static Application Security Testing (SAST)
Bandit scans Python abstract syntax trees for common security flaws (e.g. hardcoded passwords, unsafe shell execution, insecure deserialization, SQL injection).

- **Execution Command**:
  ```bash
  python -m bandit -r app/ -ll
  ```
- **Audit Outcome**:
  ```
  [main] INFO profile include tests: None
  [main] INFO run started 2026-11-12 12:20:00
  Files scanned: 26
  Lines of code: 2,410
  Total issues (by severity):
     Undefined: 0
     Low: 0
     Medium: 0
     High: 0
  Files skipped: 0
  ```
  **Result**: 0 High, 0 Medium vulnerabilities identified in application source code.

### 4.2. Software Composition Analysis (SCA) & CVE Assessment
Dependencies were evaluated using `pip-audit`.

- **Finding**: A known vulnerability exists upstream in `python-jose` (PYSEC-2026-4298 via `ecdsa`).
- **Context & Risk Analysis**:
  - MAIRA Phase 1 strictly employs HMAC-SHA256 (`HS256`) symmetric token signatures.
  - The vulnerable `ecdsa` curve logic is never invoked.
  - All token decoding functions in `app/core/security.py` strictly enforce `algorithms=["HS256"]`.
- **Roadmap & Mitigation**:
  - In Phase 2, `python-jose` will be migrated to `PyJWT>=2.8.0`, eliminating the unused `ecdsa` dependency entirely.

---

## 5. Security Checklist for Production Deployment

| Category | Requirement | Implementation Status |
|---|---|:---:|
| **Authentication** | Passwords hashed with bcrypt (12 rounds) | ✅ Verified |
| **Authentication** | Cryptographic random OTPs with email salting | ✅ Verified |
| **Authentication** | Constant-time password/OTP verification | ✅ Verified |
| **Session** | Refresh tokens hashed with SHA-256 | ✅ Verified |
| **Session** | Automatic token reuse / theft detection | ✅ Verified |
| **Session** | Short-lived access tokens (15 minutes) | ✅ Verified |
| **Authorization** | Strict RBAC enforcement (ADMIN / STUDENT) | ✅ Verified |
| **Authorization** | IDOR protection on conversational endpoints | ✅ Verified |
| **Network** | Security headers (HSTS, CSP, X-Frame-Options) | ✅ Verified |
| **Network** | CORS restricted to institutional domain | ✅ Configurable |
| **Data Protection**| Secrets masking in logs (`mask_secret`) | ✅ Verified |
| **Data Protection**| Suppression of internal stack traces in 500s | ✅ Verified |
| **Integration** | Gen AI microservice isolated from PostgreSQL | ✅ Verified |
| **Audit** | Security events logged to `sch_con.tb_con_audit_log` | ✅ Verified |
