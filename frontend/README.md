# Personal AI Assistant Frontend

## Overview

This is the Phase 6 Frontend v1 implementation for Personal AI Assistant. It is a React + TypeScript + Vite single-page app that integrates with the frozen Backend Core v1 API contracts.

Backend Core v1 remains frozen. The frontend calls the existing authentication, health, and chat endpoints without requiring backend application changes.

## Stack

- React
- TypeScript
- Vite
- Oxlint

## Directory Structure

```text
frontend/
  index.html
  package.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    App.css
    index.css
    api/
      http.ts
      auth.ts
      chat.ts
      health.ts
      types.ts
    components/
      LoginForm.tsx
      ChatInput.tsx
      ChatMessage.tsx
  public/
    favicon.svg
    icons.svg
```

## API Client Architecture

The API client lives in `src/api`.

- `http.ts` defines `fetchJson`, the shared JSON request helper.
- `ApiError` wraps non-2xx responses with HTTP status and parsed response details.
- `auth.ts` calls `POST /auth/login`.
- `chat.ts` calls `POST /chat`.
- `health.ts` calls `GET /health`.
- `types.ts` contains frontend request and response contracts that mirror Backend Core v1.

The frontend uses `VITE_API_BASE_URL` when provided. If it is unset, requests default to `/api`.

## Development Proxy

Vite proxies local `/api` requests to the backend:

```text
Frontend request: /api/chat
Vite proxy target: http://127.0.0.1:8000
Backend route: /chat
```

The proxy strips the `/api` prefix before forwarding requests. This keeps browser requests same-origin during local development while preserving the backend routes.

## Local Development

Use two separate terminals.

Terminal 1, backend:

```bash
conda activate personal-ai-env
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Terminal 2, frontend:

```bash
conda activate personal-ai-env
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Authentication Flow

1. The user signs in with email and password.
2. The frontend posts credentials to `POST /auth/login`.
3. On success, the returned JWT access token is stored in React component state only.
4. The token is sent as `Authorization: Bearer <token>` for chat requests.

The access token is stored in memory only. It is not written to local storage, session storage, cookies, or any persistent browser storage.

## Logout And Session Cleanup

Logout clears all frontend session state:

- access token
- current `conversation_id`
- displayed messages
- login errors
- chat errors
- pending send state

If a chat request returns `401`, the frontend treats the session as expired, clears the same session state, and asks the user to sign in again.

## Backend Health Check

On initial app mount, the frontend calls `GET /health` through the API client. The header displays one of three backend states:

- checking backend
- backend connected
- backend unavailable

This health check is informational. It does not block rendering the login form.

## Chat Flow

After successful login, the frontend creates a new `conversation_id` in memory. Each submitted message:

1. Adds the user message to local UI state.
2. Sends `POST /chat` with the active `conversation_id` and message text.
3. Adds the assistant response from the backend to local UI state.

The chat UI prevents duplicate in-flight sends. Failed non-authentication requests keep the current visible conversation in place and show an error.

## Conversation ID Handling

Frontend v1 creates one `conversation_id` per login session using `crypto.randomUUID()` when available, with a timestamp/random fallback. The ID remains in memory for the active session and is included in each chat request.

The ID is cleared on logout and on authentication expiry. Frontend v1 does not list, resume, rename, or persist conversations in the browser.

## Error Handling

- `401` during login displays an invalid credentials message.
- `401` during chat clears the session and prompts sign-in.
- Network failures show backend reachability messages.
- Other API failures show generic login or chat errors.
- Chat send failures keep the visible conversation state unless the failure is an authentication error.

## Current Frontend v1 Limitations

- Sign-in only; user registration remains API-only.
- Access tokens are memory-only, so refresh reloads require signing in again.
- One active in-memory conversation per login session.
- No conversation history list or resume UI.
- No memories or documents UI yet.
- No streaming responses.
- No markdown rendering or citations in chat messages.
- Backend health status is checked only on initial app mount.

## Validation

Run from `frontend/`:

```bash
npm.cmd run lint
npm.cmd run build
```
