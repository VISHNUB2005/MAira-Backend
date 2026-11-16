# MAIRA Phase 1 Frontend / Backend Integration Update

## What changed

### Frontend
- Removed the Login/Register selector and hardcoded demo credentials.
- Landing page now accepts one email and calls `POST /api/v1/auth/identify`.
- `REGISTER` starts registration OTP; `LOGIN` opens password entry.
- Registration OTP verification obtains and passes the signed registration ticket to password creation.
- Password login calls the backend and routes to email MFA when the backend returns an MFA challenge.
- MFA verification stores the returned token pair and routes by authenticated role.
- Added protected user/admin routes.
- Added a shared API client using `VITE_API_BASE_URL`, bearer access tokens, refresh-token rotation, and logout.
- User dashboard loads profile, lists/opens conversations, creates sessions, sends text prompts, and renders backend responses.
- Admin dashboard loads account analytics and student list; pre-approval uses the admin student API.
- Removed fake activity feed / hardcoded account and usage metrics where no Phase 1 endpoint exists.
- Password reset, file upload, audit feed and knowledge-source administration are not represented by the supplied Phase 1 API; these are not simulated as successful backend operations.

### Backend
- Added `POST /api/v1/auth/identify`.
- It returns `REGISTER` for an ACTIVE allowlisted user/admin with `password_hash IS NULL`.
- It returns `LOGIN` for an ACTIVE allowlisted user/admin with a non-NULL password hash.
- Unknown and inactive accounts receive the same generic not-eligible response.
- Endpoint is rate-limited by client IP.
- Added integration tests for REGISTER/LOGIN routing and generic rejection.
- Updated default CORS origins for Vite (`localhost:5173` and `127.0.0.1:5173`).
- Corrected `.env.example` names to match the current settings model.
- Backend startup DB log now prints the configured database name.

## Important local configuration

Frontend `.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Backend `.env` must allow:
```env
CORS_ALLOW_ORIGINS_RAW=http://localhost:5173,http://127.0.0.1:5173
```

Do not overwrite your existing backend `.env` when extracting the update. It contains machine-specific credentials and secrets. The backend ZIP intentionally excludes `.env`.

## Database safety

The supplied local backend `.env` was configured for `mira_db`. Keep it that way only when intentionally running against the institutional environment with authorization. For local write-based testing, configure `DB_NAME=mira_test_db` and ensure that database has the approved `sch_con` schema and test fixtures first. Do not test OTP, registration, password creation, admin pre-approval, or chat writes against institutional `mira_db`.

The automated integration tests use `TEST_DB_NAME` (default `mira_test_db`) and have a guard against `mira_db`. The test-database setup script was also updated to use the configured PostgreSQL connection settings rather than a hardcoded password. Backend source and test files passed Python syntax compilation. The new integration tests were not executed here because this environment did not have the `asyncpg` driver / configured PostgreSQL test database. The frontend production build was not verified here: the ZIP's bundled `node_modules` contained Windows-only native packages, and dependency installation timed out in this environment. The frontend archive omits `node_modules`; run `npm install` on your Windows machine before starting it.

## Run locally

1. Extract the backend update over your existing `mAira-Backend` source folder, keeping your existing `.env`.
2. Extract the frontend update over the frontend repository's `frontend` folder.
3. In the frontend folder, run `npm install`, then `npm run dev`.
4. Start the backend with `python scripts/run_dev.py`.
5. Open the Vite URL (normally `http://localhost:5173`).

The frontend uses the backend API; the Gen AI service remains behind the backend and is never called directly from the browser.
