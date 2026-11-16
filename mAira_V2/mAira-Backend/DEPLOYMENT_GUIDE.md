# MAIRA Phase 1 Backend — Production Deployment & Operations Guide

This guide establishes the production readiness checklist, deployment architecture, secrets management, process management, database hardening, and operational runbooks for the MAIRA Phase 1 Backend.

---

## 1. Production Readiness Checklist

Before promoting any build of MAIRA Phase 1 to staging or production, verify every requirement on this checklist:

| Verification Item | Verification Criteria | Status |
|---|---|:---:|
| **Environment Flag** | `ENVIRONMENT=production` in environment or secret store | [ ] |
| **Debug Mode** | FastAPI/Uvicorn `reload=False`, `echo=False` on database engine | [ ] |
| **Secret Entropy** | `JWT_SECRET_KEY` and `GENAI_SERVICE_KEY` minimum 32 random bytes | [ ] |
| **No Cleartext Credentials** | Zero passwords, tokens, or credentials checked into Git | [ ] |
| **Database Preflight** | `python scripts/verify_db.py` confirms all 7 tables in `sch_con` | [ ] |
| **Automated Tests** | `python -m pytest tests/ -v` completes with 100% pass rate (45/45) | [ ] |
| **Security Scanning** | `bandit -r app/ -ll` reports 0 High and 0 Medium issues | [ ] |
| **CORS Restriction** | `CORS_ORIGINS` strictly limited to institutional domains | [ ] |
| **Email Dispatcher** | `EMAIL_PROVIDER=smtp` configured with verified institutional SMTP | [ ] |
| **Rate Limiter** | `RATE_LIMIT_ENABLED=true` active | [ ] |
| **TLS/HTTPS** | Reverse proxy configured with TLS 1.3 and valid certificate | [ ] |

---

## 2. Secrets Management Architecture

MAIRA Phase 1 utilizes the multi-tiered `app.security.secrets` provider to load configuration securely without writing cleartext credentials to disk.

```
Priority 1: Environment Variables (e.g. JWT_SECRET_KEY)
Priority 2: File Pointers (e.g. JWT_SECRET_KEY_FILE=/var/run/secrets/jwt_secret)
Priority 3: Docker / K8s Mounted Secrets (/run/secrets/*)
```

### 2.1. Generating Cryptographically Secure Secrets
Generate production keys using standard CSPRNG tools:
```bash
# Generate 256-bit URL-safe secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2. Kubernetes / Docker Secrets Configuration
Mount secrets into `/run/secrets/`:
- `/run/secrets/postgres_password`
- `/run/secrets/jwt_secret_key`
- `/run/secrets/genai_service_key`
- `/run/secrets/smtp_password`

The backend automatically detects and mounts these files without requiring environment variable overrides.

---

## 3. Server Process Execution & Systemd Configuration

In Linux production environments, execute MAIRA using Gunicorn managing worker processes of Uvicorn's asynchronous worker class.

### 3.1. Process Command
```bash
gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --timeout 60 \
  --keep-alive 5 \
  --access-logfile /var/log/maira/access.log \
  --error-logfile /var/log/maira/error.log \
  app.main:app
```

### 3.2. Systemd Service Unit (`/etc/systemd/system/maira-backend.service`)
```ini
[Unit]
Description=MAIRA Phase 1 FastAPI Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=maira
Group=maira
WorkingDirectory=/opt/maira/mAira-Backend
EnvironmentFile=/etc/maira/maira.env
ExecStart=/opt/maira/mAira-Backend/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile - \
    --error-logfile - \
    app.main:app
Restart=always
RestartSec=5s
KillMode=mixed
TimeoutStopSec=30s
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable maira-backend
sudo systemctl start maira-backend
sudo systemctl status maira-backend
```

---

## 4. Production Reverse Proxy Configuration (Nginx)

Place an Nginx reverse proxy in front of the backend to terminate TLS, enforce HTTP/2, and provide client IP forwarding.

```nginx
upstream maira_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

server {
    listen 80;
    server_name api.maira.institution.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.maira.institution.edu;

    ssl_certificate /etc/letsencrypt/live/api.maira.institution.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.maira.institution.edu/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Edge Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none';" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://maira_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $http_x_request_id;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 30s;
    }
}
```

---

## 5. Containerized Deployment (Docker Compose)

```yaml
version: "3.8"

services:
  maira-backend:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=mira_db
      - POSTGRES_SCHEMA=sch_con
      - POSTGRES_USER=maira_user
      - GENAI_SERVICE_URL=http://genai-service:8001
      - EMAIL_PROVIDER=smtp
      - CORS_ORIGINS=["https://maira.institution.edu"]
    secrets:
      - postgres_password
      - jwt_secret_key
      - genai_service_key
      - smtp_password
    depends_on:
      - postgres

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  jwt_secret_key:
    file: ./secrets/jwt_secret.txt
  genai_service_key:
    file: ./secrets/genai_service_key.txt
  smtp_password:
    file: ./secrets/smtp_password.txt
```

---

## 6. Database Hardening & Backup Policy

### 6.1. Connection Sizing
Each Uvicorn worker maintains an independent connection pool:
$$\text{Max DB Connections} = \text{Workers} \times (\text{DB\_POOL\_SIZE} + \text{DB\_MAX\_OVERFLOW})$$
For 4 workers with `pool_size=10, max_overflow=20`:
$$\text{Max Connections} = 4 \times 30 = 120\text{ connections}$$
Ensure PostgreSQL `max_connections` in `postgresql.conf` is set to $\ge 150$.

### 6.2. Schema-Specific Automated Backup Runbook
Execute daily backups targeting schema `sch_con` with compression:
```bash
pg_dump \
  -h localhost \
  -U postgres \
  -d mira_db \
  -n sch_con \
  -F c \
  -f /var/backups/maira/mira_db_sch_con_$(date +%Y%m%d_%H%M%S).dump
```

Verify backup integrity:
```bash
pg_restore -l /var/backups/maira/mira_db_sch_con_*.dump | head -n 20
```

---

## 7. Monitoring, Observability & Incident Response

### 7.1. Health Endpoint Probing
Configure Prometheus, UptimeRobot, or Kubernetes liveness probes against:
- **Liveness Probe**: `GET /health` (every 15s)
- **Readiness Probe**: `GET /health` (every 5s, checks DB connection pool)

### 7.2. Critical Operational Alerts
Trigger PagerDuty / OpsGenie incidents for:
1. **Database Disconnected**: `/health` returns HTTP 503.
2. **Elevated Gen AI Timeouts**: Spikes in HTTP 504 on `/api/v1/chat/sessions/{id}/messages`.
3. **Security Alarms**: Any occurrence of `REFRESH_TOKEN_REUSE_DETECTED` in `sch_con.tb_con_audit_log`.

### 7.3. Emergency Credential Invalidation Runbook
If an institutional account is compromised, execute immediate session termination:
```sql
-- Revoke all active sessions for a specific user ID
UPDATE sch_con.tb_con_user_sessions
SET is_revoked = TRUE
WHERE account_id = 'compromised-account-uuid';

-- Record administrative revocation in audit log
INSERT INTO sch_con.tb_con_audit_log (id, actor_id, actor_type, action, resource_type, resource_id, status, details, created_at)
VALUES (
    gen_random_uuid(),
    'admin-account-uuid',
    'ADMIN',
    'EMERGENCY_SESSION_REVOCATION',
    'USER',
    'compromised-account-uuid',
    'SUCCESS',
    '{"reason": "Administrative emergency containment"}',
    NOW()
);
```
