# Personal AI Assistant Frontend

## Overview

This is the React + TypeScript + Vite frontend for Personal AI Assistant. It integrates with the frozen Backend Core v1 API contracts for authenticated chat, explicit memories, document uploads, Knowledge/RAG retrieval modes, and citation rendering.

Backend Core v1 remains frozen. The frontend calls the existing authentication, health, chat, memory, and document endpoints without requiring incompatible backend API changes.

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
      documents.ts
      health.ts
      memories.ts
      types.ts
    components/
      LoginForm.tsx
      ChatInput.tsx
      ChatMessage.tsx
      DocumentList.tsx
      DocumentUpload.tsx
      KnowledgeModeSelector.tsx
      KnowledgeSources.tsx
      MemoryModeSelector.tsx
      MemorySection.tsx
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
- `documents.ts` calls `/documents` upload, list, fetch, and search endpoints.
- `health.ts` calls `GET /health`.
- `memories.ts` calls `/memories` create, list, and delete endpoints.
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
4. The token is sent as `Authorization: Bearer <token>` for chat and document requests.

The access token is stored in memory only. It is not written to local storage, session storage, cookies, or any persistent browser storage.

## Logout And Session Cleanup

Logout clears all frontend session state:

- access token
- current `conversation_id`
- displayed messages
- uploaded document list
- saved memory list
- selected knowledge mode
- selected memory mode
- login errors
- chat errors
- document errors
- memory errors
- pending send state

If a chat, memory, or document request returns `401`, the frontend treats the session as expired, clears the same session state, and asks the user to sign in again. Logout clears frontend memory state but does not delete stored memories.

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
4. Renders memory usage, retrieval warnings, source citations, or no-source state when returned in response metadata.

The chat UI prevents duplicate in-flight sends. Failed non-authentication requests keep the current visible conversation in place and show an error.

## Memory UI

After login, the frontend loads the authenticated user's saved memories and shows a compact Memory section. Users can manually save a memory with category, key, and value fields, list saved memories, and delete a memory. Creating a memory with an existing key updates that saved fact on the backend.

The Memory selector maps UI modes to the backend-compatible `memory_retrieval` field:

- Auto sends `null`.
- Always sends `true`.
- Never sends `false`.

Assistant messages render a subtle "Used memory" indicator when `metadata.memory.retrieval_count` is greater than zero. Chat metadata exposes category/key source summaries, not internal memory database IDs.

## Knowledge UI

After login, the frontend loads the authenticated user's document list and shows a Knowledge panel. The upload control accepts PDF, DOCX, TXT, Markdown `.md`, and Markdown `.markdown` files. Failed documents remain visible with their backend error message and `failed` status.

The Knowledge selector maps UI modes to the backend-compatible `knowledge_retrieval` field:

- Auto sends `null`.
- Always sends `true`.
- Never sends `false`.

Assistant messages render `metadata.knowledge.sources` as document citations with chunk section and character offsets. Retrieval warnings are shown below the assistant message. In Always mode, an empty retrieval result shows "No document sources found."

Memory and Knowledge controls are independent. Disabling Memory does not disable document retrieval, and disabling Knowledge does not disable memory retrieval.

## Conversation ID Handling

Frontend v1 creates one `conversation_id` per login session using `crypto.randomUUID()` when available, with a timestamp/random fallback. The ID remains in memory for the active session and is included in each chat request.

The ID is cleared on logout and on authentication expiry. Frontend v1 does not list, resume, rename, or persist conversations in the browser.

## Error Handling

- `401` during login displays an invalid credentials message.
- `401` during chat or document requests clears the session and prompts sign-in.
- Network failures show backend reachability messages.
- Other API failures show generic login or chat errors.
- Chat send failures keep the visible conversation state unless the failure is an authentication error.

## Current Frontend Limitations

- Sign-in only; user registration remains API-only.
- Access tokens are memory-only, so refresh reloads require signing in again.
- One active in-memory conversation per login session.
- No conversation history list or resume UI.
- No document preview or source deep-linking.
- No streaming responses.
- No markdown rendering for assistant text.
- Backend health status is checked only on initial app mount.

## Validation

Run from `frontend/`:

```bash
npm.cmd run lint
npm.cmd run build
```
