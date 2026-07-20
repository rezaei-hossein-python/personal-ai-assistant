# Project Overview

## Purpose

Personal AI Assistant is being developed into a modular personal AI operating system. The current project includes a frozen Backend Core v1 API, Knowledge/RAG v1, and a React frontend for authenticated chat with document-backed retrieval. The backend includes authenticated chat, user-owned memory and documents, RAG, lightweight agent orchestration, and deterministic multi-model provider routing.

Backend Core v1 remains frozen. The frontend integrates with its existing API contracts and does not require incompatible backend application changes.

## Current Backend

- FastAPI application in `app/main.py`
- Routers for health, authentication, chat, memories, and documents
- SQLAlchemy models for users, conversations, messages, memories, documents, and document chunks
- Alembic migrations for database schema management
- PostgreSQL as the expected runtime database
- pgvector-backed semantic document search
- Chat orchestrator coordinating lightweight planner, memory, knowledge, action, and evaluator agents
- Provider-neutral model interface and router
- OpenAI, Gemini, Claude, and Grok generation providers
- JWT bearer-token authentication
- User-owned conversations, memories, and documents
- PDF, DOCX, TXT, and Markdown text extraction
- Reusable text chunking with OpenAI embeddings stored as pgvector vectors
- OpenAI Responses API integration for default chat, embeddings, and memory extraction

## Current Frontend

- React + TypeScript + Vite application in `frontend/`
- Local frontend URL: `http://localhost:5173`
- Backend API URL: `http://127.0.0.1:8000`
- Vite `/api` development proxy to the backend with prefix rewrite
- Shared JSON API helper in `frontend/src/api/http.ts`
- Endpoint-specific clients for authentication, chat, and health
- TypeScript request/response contracts in `frontend/src/api/types.ts`
- Sign-in form backed by `POST /auth/login`
- Backend health indicator backed by `GET /health`
- Real chat flow backed by `POST /chat`
- Knowledge document upload and listing backed by `/documents`
- Auto, Always, and Never knowledge retrieval selector
- Citation/source rendering for retrieved document chunks
- Logout and session cleanup behavior
- Responsive single-page chat UI

Frontend directory structure:

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
      DocumentList.tsx
      DocumentUpload.tsx
      KnowledgeModeSelector.tsx
      KnowledgeSources.tsx
  public/
    favicon.svg
    icons.svg
```

Frontend API client architecture:

- `fetchJson` centralizes JSON request/response handling.
- `ApiError` captures non-2xx status codes and parsed error details.
- Bearer tokens are attached only when an access token is supplied.
- `VITE_API_BASE_URL` can override the default API base URL.
- When `VITE_API_BASE_URL` is unset, requests use `/api` and the Vite proxy forwards them to `http://127.0.0.1:8000`.

## Current Request Flow

```text
Frontend startup
  render React app
  call GET /health through /api proxy
  display backend status
  render sign-in form
```

```text
Frontend authentication
  user submits email and password
  POST /auth/login
  store returned access token in React state only
  create in-memory conversation_id
  render chat UI
```

```text
Frontend chat
  user submits message
  append local user message
  POST /chat with bearer token, conversation_id, message, and knowledge_retrieval mode
  append assistant response
  render retrieval warnings, no-source state, or citation/source metadata
  preserve visible messages on non-authentication chat errors
```

```text
Knowledge/RAG v1 document flow
  authenticated user uploads TXT, Markdown, DOCX, or PDF
  backend extracts text
  backend normalizes and chunks text
  chunk metadata stores start/end character offsets
  embedding provider embeds each chunk
  documents and chunks are stored under the authenticated user
  PostgreSQL stores chunk embeddings with pgvector
  chat query is embedded when retrieval is enabled
  user-scoped vector search returns relevant chunks
  retrieved chunks are injected into prompt context
  model response is returned with citation metadata
  React renders sources, warnings, or no-source state
```

The frontend access token is memory-only. It is not stored in local storage, session storage, cookies, or another persistent browser store.

Logout and `401` chat or document responses clear the access token, current `conversation_id`, displayed messages, document list, selected knowledge mode, errors, and pending state.

```text
POST /chat
  verify bearer token
  load current user
  call ChatOrchestrator
  PlannerAgent selects intent and capabilities
  MemoryAgent loads user memory context
  KnowledgeAgent retrieves document context when needed
  ActionAgent returns no-op action metadata
  ModelRouter selects provider and records fallback metadata
  model provider generates response
  EvaluatorAgent records context warnings
  persist conversation messages
  return response
```

```text
POST /documents/upload
  verify bearer token
  load current user
  detect supported file type
  extract text
  chunk text
  generate embeddings
  store document metadata
  store chunks and embeddings linked to the document
```

Knowledge modes:

- Auto sends `knowledge_retrieval: null`; the planner enables retrieval for document/knowledge/search prompts.
- Always sends `knowledge_retrieval: true`; retrieval runs even for general prompts.
- Never sends `knowledge_retrieval: false`; retrieval is disabled even if the planner would select knowledge.

Citation metadata is returned under `metadata.knowledge.sources` with document ID, document name, chunk ID, chunk index, character offsets, and vector distance. Retrieval remains scoped to the authenticated user; User A cannot list, search, or retrieve User B documents.

## Local Development

1. Activate the Conda environment.

   ```bash
   conda activate personal-ai-env
   ```

2. Install backend dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Configure `.env`.

   ```bash
   APP_ENV=development
   OPENAI_API_KEY=your_api_key_here
   OPENAI_MODEL=gpt-4.1-mini
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   GEMINI_API_KEY=
   GEMINI_MODEL=gemini-1.5-flash
   ANTHROPIC_API_KEY=
   ANTHROPIC_MODEL=claude-3-5-sonnet-latest
   XAI_API_KEY=
   XAI_MODEL=grok-2-latest
   MODEL_PROVIDER_DEFAULT=openai
   MODEL_COLLABORATION_ENABLED=false
   SECRET_KEY=replace_with_a_long_random_secret
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/personal_ai
   ```

4. Run migrations.

   ```bash
   alembic upgrade head
   ```

5. Start the API in the first terminal.

   ```bash
   uvicorn app.main:app --reload
   ```

   Backend URL: `http://127.0.0.1:8000`

6. Start the frontend in a second terminal.

   ```bash
   conda activate personal-ai-env
   cd frontend
   npm run dev
   ```

   Frontend URL: `http://localhost:5173`

7. Run backend tests.

   ```bash
   pytest
   ```

8. Run frontend validation from `frontend/`.

   ```bash
   npm.cmd run lint
   npm.cmd run build
   ```

The backend and frontend development servers run in separate terminals.

## Current Limitations

- Sign-in only; registration remains API-only.
- Access token is memory-only, so browser refresh requires signing in again.
- One active in-memory conversation per login session.
- No conversation history list or resume UI.
- No memories UI.
- No document preview or source deep-linking.
- No streaming responses.
- No markdown rendering for assistant text.
- Backend health check runs only on initial app mount.
- Runtime semantic retrieval requires PostgreSQL with pgvector.
- Uploaded original document binaries are not retained; extracted chunks and metadata are stored.
- Retrieval uses top-k vector similarity without reranking or manual source selection.

## Architecture Direction

Future phases will add:

- richer agent tools and task execution
- richer long-term memory modeling
- richer multi-provider model evaluation
- Approved tool/action execution
- frontend registration, conversation history, memories, documents, tasks, and settings
