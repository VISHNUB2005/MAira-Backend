# mAIra Frontend

React + Vite frontend connected to the MAIRA Phase 1 FastAPI backend.

## Local setup

1. Start the backend from its project directory.
2. Ensure the backend `.env` allows the Vite origin:
   `CORS_ALLOW_ORIGINS_RAW=http://localhost:5173,http://127.0.0.1:5173`
3. In this frontend directory, create `.env` from `.env.example` if you need a different backend URL.
4. Install dependencies and run:

```powershell
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`).

## Backend URL

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`.

## Phase 1 authentication

- One email entry calls `POST /api/v1/auth/identify`.
- `next_step=REGISTER` starts registration OTP and password creation.
- `next_step=LOGIN` opens password login, then email MFA.
- Access and refresh tokens are held in `sessionStorage` for the current browser tab.
- Authenticated dashboard routes are guarded by role.
- Session refresh and logout use the backend APIs.

## Phase 1 chat

- The frontend creates and lists chat sessions using `/api/v1/chat/sessions`.
- It loads saved conversation history and sends text prompts to the backend.
- The backend remains responsible for calling the separate Gen AI microservice.
- File uploads are not supported by the supplied Phase 1 API and are not submitted.

## Current API scope limitations

The supplied backend OpenAPI does not include password-reset endpoints, file-upload endpoints, an audit/activity feed, or knowledge-base administration endpoints. The UI does not simulate these backend operations. Password recovery currently directs the user to the institutional administrator.
