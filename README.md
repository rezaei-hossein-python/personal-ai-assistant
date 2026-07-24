# Personal AI Assistant

## Overview

Personal AI Assistant is an early-stage personal AI operating system. The current system includes a frozen Backend Core v1 FastAPI API, Frontend v1, Knowledge/RAG v1, Long-Term Memory v1, Conversation History v1, Actions & Tools v1, Phase 11 Deployment and Production Hardening v1, Phase 12 Windows Desktop Application v1, and Phase 15 Offline Instant Writing Reviser v1. The backend supports authenticated chat, message history, memory management, document ingestion, RAG, lightweight agent orchestration, deterministic multi-model provider routing, production configuration validation, migrations, health/readiness checks, container builds, CI validation, a local Windows desktop mode, and a Windows-wide offline writing hotkey.

## Current Architecture

```text
Frontend
  frontend/
    React + TypeScript + Vite
    http://localhost:5173
    /api development proxy to Backend Core v1
    login, backend health, chat, conversation history, saved memories, knowledge uploads, citations, logout/session cleanup

Backend Core v1
  app/main.py
    http://127.0.0.1:8000
    /health
    /auth/register
    /auth/login
    /chat
    /conversations
    /memories
    /documents

Routers
  app/routers/auth.py
  app/routers/chat.py
  app/routers/conversations.py
  app/routers/documents.py
  app/routers/memories.py
  app/routers/health.py

Services
  Chat orchestration
  Lightweight planner, memory, knowledge, action, and evaluator agents
  Provider-neutral model interface and router
  User registration/login
  Password hashing
  JWT access tokens
  OpenAI, Gemini, Claude, and Grok generation providers
  OpenAI embedding provider abstraction
  Explicit long-term memory CRUD and retrieval
  Document parsing and chunking
  Retrieval/RAG prompt context
  Conversation/message persistence
  Memory and document CRUD
  Offline writing revision service isolated from cloud chat providers

Database
  PostgreSQL + pgvector for development/cloud semantic search
  SQLite desktop mode with Python cosine retrieval
  SQLAlchemy ORM
  Alembic migrations

Models
  User
  Conversation
  Message
  Memory
  Document
  DocumentChunk
```

Backend Core v1 compatibility is preserved. Conversation History v1 adds authenticated history APIs and frontend history UI while keeping the existing `/chat` request behavior intact.

## Frontend V1

The frontend is a React + TypeScript + Vite app in `frontend/`.

```text
frontend/src/
  App.tsx
  api/
    http.ts
    auth.ts
    chat.ts
    conversations.ts
    health.ts
    types.ts
  components/
    LoginForm.tsx
    ChatInput.tsx
    ChatMessage.tsx
    ConversationSidebar.tsx
```

API requests are centralized through `frontend/src/api/http.ts`. The shared `fetchJson` helper JSON-encodes request bodies, parses JSON responses, attaches bearer tokens when provided, and raises `ApiError` for non-2xx responses. Endpoint-specific clients live in `auth.ts`, `chat.ts`, and `health.ts`.

Vite proxies `/api` to `http://127.0.0.1:8000` during development and strips the `/api` prefix before forwarding. The frontend URL is `http://localhost:5173`.

Authentication uses `POST /auth/login`. The returned access token is stored in React state only and is not persisted to local storage, session storage, or cookies. Login loads saved conversations, memories, and documents. Logout clears only frontend session state; server-side conversation history is retained. A `401` from authenticated API calls performs the same session cleanup and asks the user to sign in again.

Chat uses `POST /chat` with a frontend-generated `conversation_id` and message text. New Chat clears the active messages and `conversation_id` without deleting previous conversations. The next sent message creates a new frontend `conversation_id`; continuing or selecting a conversation reuses its existing ID.

On initial app mount, the frontend calls `GET /health` and displays backend status. Network and API failures are shown as user-facing login or chat errors; non-authentication chat failures keep the visible conversation state.

Frontend limitations: sign-in only, access tokens persist in browser local storage for refresh recovery, no server-side token revocation, no streaming responses, no markdown rendering for assistant text, no document preview, and a health check only on initial app mount. Historical messages load role/content/timestamp only because citation and memory metadata are not persisted yet.

## Accessibility

Phase 13 hardens the web and desktop UI for keyboard use, semantic structure, accessible names, status announcements, visible focus, contrast, zoom/reflow, reduced motion, and destructive-action confirmations. The interface is designed and tested toward WCAG 2.2 Level AA where applicable; this is not a formal conformance certification.

Run the automated accessibility checks from `frontend/`:

```cmd
npm.cmd run test:a11y
```

See [Accessibility Guide](docs/accessibility.md) for the audit findings, implementation approach, Narrator checklist, NVDA follow-up checklist, and known limitations.

## Requirements

- Python 3.12+
- Node.js 24 for frontend development/builds
- PostgreSQL
- pgvector extension for semantic document search
- OpenAI API key for the default provider and embeddings
- Optional Gemini, Anthropic, and xAI API keys for routed generation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Local Configuration

Create `.env` from `.env.example`:

```bash
APP_NAME=Personal AI Assistant
APP_VERSION=0.1.0
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

PostgreSQL is the expected database for browser/server development and cloud deployment. SQLite is supported for tests with `APP_ENV=test` and for Windows desktop mode with `DESKTOP_MODE=true` and `DATABASE_BACKEND=sqlite`.

Production uses the typed settings in `app/config.py`. Set `APP_ENV=production`, `DEBUG=false`, a strong `JWT_SECRET_KEY`, exact `ALLOWED_ORIGINS`, exact `TRUSTED_HOSTS`, and `API_DOCS_ENABLED=false`. Missing production secrets fail startup clearly.

Semantic document search in PostgreSQL mode requires the `vector` extension. Knowledge/RAG v1 stores embeddings in `document_chunks.embedding vector(1536)` and uses pgvector cosine similarity retrieval. SQLite desktop mode stores embeddings as JSON and calculates cosine distance in Python for personal-scale document collections.

## Windows Desktop Application v1

Desktop v1 runs the existing backend and frontend locally without a public server:

```cmd
.\.conda\python.exe -m desktop.main
```

Build the portable Windows package:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_desktop.ps1
```

Output:

```text
dist\PersonalAIAssistant\PersonalAIAssistant.exe
```

Desktop mode uses `pywebview`, starts FastAPI automatically on `127.0.0.1` with an automatically selected port, serves the compiled React bundle locally, and stops the backend when the desktop window closes. Mutable desktop data is stored under:

```text
%LOCALAPPDATA%\PersonalAIAssistant
```

OpenAI remains the default AI provider. Internet access is still required for OpenAI API requests, and usage may cost money. The OpenAI API key is stored through Windows Credential Manager via Python `keyring`; it is not embedded in frontend JavaScript or packaged resources.

See [Desktop Application Guide](docs/desktop-application.md) for architecture, packaging, backup, troubleshooting, limitations, and the manual regression checklist.

## Offline Instant Writing Reviser v1

The offline writing reviser is packaged as a separate silent Windows background executable. Select editable English text in another application, press `Ctrl+Alt+W`, and the selected text is replaced with polished natural English when the local model succeeds. Successful revision displays no chat, no feedback, no score, and no confirmation dialog.

This path is isolated from chat and cloud model routing. It uses the local `ollama` executable with the configured local model, defaults to `llama3.2:3b`, and never falls back to OpenAI or another remote provider. Install Ollama and the model explicitly before use:

```cmd
winget install Ollama.Ollama
ollama pull llama3.2:3b
```

Build the background reviser:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_writing_reviser.ps1
```

Output:

```text
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe
```

Optional per-user Windows startup is explicit:

```cmd
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe --enable-startup
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe --disable-startup
```

See [Offline Instant Writing Reviser](docs/offline-writing-reviser.md) for architecture, privacy guarantees, configuration, troubleshooting, and the mandatory offline manual validation checklist.

## Model Providers

Generation is routed through a provider-neutral `ModelRouter`. Provider API keys are optional per provider, and the application can start with only OpenAI configured.

Routing policy:

- General reasoning: configured default provider, OpenAI by default
- Long-form document analysis and document search: Claude when configured
- Multimodal-capable prompts such as images or screenshots: Gemini when configured
- Real-time or social-context prompts: Grok when configured

If the preferred provider is not configured, lacks text-generation capability, or raises a provider availability error, the router falls back to the configured default provider and records the event in internal execution metadata. OpenAI remains the default embedding provider for document ingestion and search.

Optional collaboration mode can be enabled with `MODEL_COLLABORATION_ENABLED=true`. It is limited to selected combined-context tasks and invokes only a small number of configured collaborators before final synthesis.

## Database Migrations

Apply migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "Describe change"
```

## Run Locally

Use separate terminals for the backend and frontend.

Terminal 1, backend:

```bash
conda activate personal-ai-env
uvicorn app.main:app --reload
```

Backend URL:

```bash
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Readiness check:

```bash
curl http://127.0.0.1:8000/ready
```

Terminal 2, frontend:

```bash
conda activate personal-ai-env
cd frontend
npm run dev
```

Frontend URL:

```bash
http://localhost:5173
```

## Authentication

Register a user:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"name\":\"Your Name\",\"password\":\"your-password\"}"
```

Log in to get a bearer token:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"your-password\"}"
```

Use the token with protected endpoints:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"conversation_id\":\"default\",\"message\":\"Hello\"}"
```

Memory endpoints are also protected:

```bash
curl http://127.0.0.1:8000/memories \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Conversation History V1

Conversation History v1 reuses the existing `Conversation` and `Message` models:

```text
Conversation
  id
  user_id
  conversation_id
  title
  created_at

Message
  id
  user_id
  conversation_id
  role
  content
  created_at
```

`POST /chat` remains backward-compatible. Existing clients keep sending `conversation_id`; the backend gets or creates the current user's conversation, saves the user message, generates the assistant response, then saves the assistant message. Failed assistant generations are not stored as successful assistant messages.

Conversation APIs are authenticated and user-scoped:

```bash
curl http://127.0.0.1:8000/conversations \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

```bash
curl http://127.0.0.1:8000/conversations/default \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

```bash
curl -X DELETE http://127.0.0.1:8000/conversations/default \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

`GET /conversations` returns summaries sorted by latest message activity where possible. The frontend uses the stored title unless it is the default title, then derives a compact label from the first user message or falls back to "New conversation". V1 does not generate AI titles.

Selecting a conversation loads ordered persisted messages, sets the active `conversation_id`, and renders the chat. Logout clears the local conversation list and active chat but does not delete server-side history. Logging in again reloads the history.

Knowledge/RAG and Memory behavior are unchanged. Live `/chat` responses still include citation and memory metadata. Historical messages do not currently store that metadata, so historical citation and memory badges may only appear for messages still in the current frontend session.

## Long-Term Memory V1

Memory v1 stores user-scoped facts and preferences in the existing `memories` table:

```text
Memory
  id
  user_id
  category
  key
  value
  created_at
  updated_at
```

Memory creation is explicit. The assistant does not automatically save every chat message or silently extract sensitive facts from conversation text. Users save memories through `POST /memories` or the authenticated frontend Memory section.

Create or update a memory:

```bash
curl -X POST http://127.0.0.1:8000/memories \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"category\":\"preference\",\"key\":\"favorite_programming_language\",\"value\":\"Python\"}"
```

List saved memories:

```bash
curl http://127.0.0.1:8000/memories \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Delete a memory:

```bash
curl -X DELETE http://127.0.0.1:8000/memories/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Chat memory modes are controlled by optional `memory_retrieval` on `POST /chat`:

- `null` or omitted: Auto. The planner/default behavior decides whether memory retrieval runs.
- `true`: Always. User-scoped memory retrieval runs even if the planner would not select memory.
- `false`: Never. Memory retrieval is disabled even if the planner would select memory.

Memory retrieval is deterministic for v1. It tokenizes the chat message, scores the authenticated user's memories by category, key, and value overlap, and injects the top matching memories into the model prompt as known user information. No vector memory pipeline is required for v1, but the service boundary leaves room for future embedding-based memory retrieval.

Retrieved memories never cross user boundaries. Listing, deletion, and chat retrieval all filter by authenticated `user_id`; deleting another user's memory returns `404`.

Chat responses include memory metadata:

```json
{
  "metadata": {
    "memory": {
      "enabled": true,
      "mode": "planner",
      "retrieval_count": 1,
      "sources": [
        {
          "category": "preference",
          "key": "favorite_programming_language"
        }
      ]
    }
  }
}
```

Internal memory IDs are used for CRUD endpoints but are not shown as chat source metadata. The React UI shows a subtle "Used memory" indicator on assistant messages when memory contributed to the response.

Memory and Document Knowledge are independent context systems:

- Memory stores compact user facts and preferences manually saved by the user.
- Document Knowledge stores uploaded document chunks with embeddings and source metadata.
- Both can contribute to the same response when both retrieval modes are enabled by the planner or explicit controls.
- Disabling Memory does not disable Knowledge, and disabling Knowledge does not disable Memory.

Current Memory v1 limitations:

- No automatic memory extraction from chat.
- No memory embeddings, semantic reranker, provenance graph, or relationship modeling.
- Memory prompt context is limited to top deterministic matches.
- The frontend supports one compact memory list/form, not bulk editing or advanced memory review.

## Knowledge/RAG V1

Supported upload formats:

- PDF: `application/pdf`, `.pdf`
- DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `.docx`
- TXT: `text/plain`, `.txt`
- Markdown: `text/markdown`, `text/x-markdown`, `.md`, `.markdown`

Upload a document:

```bash
curl -X POST http://127.0.0.1:8000/documents/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@notes.md;type=text/markdown"
```

List your documents:

```bash
curl http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Get document metadata:

```bash
curl http://127.0.0.1:8000/documents/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Delete a document and its chunks:

```bash
curl -X DELETE http://127.0.0.1:8000/documents/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Search documents:

```bash
curl -X POST http://127.0.0.1:8000/documents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"query\":\"project architecture\",\"limit\":5}"
```

Architecture:

```text
Document upload
  POST /documents/upload with bearer token
  text extraction by file type
  normalized text chunking with start/end character metadata
  embedding generation for each chunk
  document and chunks persisted under the authenticated user
  chunk embeddings stored in PostgreSQL/pgvector

Chat retrieval
  POST /chat with bearer token
  ChatOrchestrator
    PlannerAgent selects intent/capabilities
    KnowledgeAgent embeds query text when retrieval is enabled
    user-scoped pgvector similarity search returns matching chunks
    PromptService injects retrieved chunks into model context
    ModelRouter selects a configured ModelProvider
    ModelProvider generates a response
    response metadata includes citation/source records for the UI
```

End-to-end flow:

```text
Document upload
-> text extraction
-> chunking
-> embeddings
-> PostgreSQL/pgvector
-> query embedding
-> user-scoped retrieval
-> prompt context
-> model response
-> citation metadata
-> React UI
```

The ingestion pipeline creates a `documents` row for the authenticated user, extracts text, normalizes and chunks text with `start_character` and `end_character` metadata, embeds each chunk, and stores chunks in `document_chunks`. A failed extraction or embedding step marks the document as `failed` with an error message; failed documents remain visible in the frontend document list.

Retrieval is always scoped by authenticated `user_id`. A user can list, fetch, delete, search, and retrieve only their own documents and chunks. The search endpoint and chat retrieval both join chunks through their owning document before returning results.

Knowledge modes are controlled by the optional `knowledge_retrieval` field on `POST /chat`:

- `null` or omitted: Auto. The planner enables retrieval for document/knowledge/search-style prompts.
- `true`: Always. Retrieval runs even if the planner would not select knowledge.
- `false`: Never. Retrieval is disabled even if the planner would select knowledge.

Citation metadata is returned under `metadata.knowledge.sources` with document ID, document name, chunk ID, chunk index, character offsets, and distance. The React UI renders sources below assistant messages, displays retrieval warnings, and shows "No document sources found" when Always mode runs retrieval but finds no sources.

Documents uploaded after Phase 3.1 receive embeddings during ingestion. Documents uploaded before the embedding column existed may need to be re-uploaded or backfilled before they appear in semantic search results.

Backfill missing chunk embeddings:

```bash
python scripts/backfill_embeddings.py
```

The backfill command is idempotent: it skips chunks that already have embeddings and reports scanned, updated, skipped, and failed counts.

Current Knowledge/RAG v1 limitations:

- Semantic retrieval requires PostgreSQL with pgvector in runtime environments.
- The frontend shows source document names and chunk locations, but it does not open an in-document preview.
- Uploaded document files are not stored as original binary blobs; extracted text chunks and metadata are stored.
- Retrieval uses top-k similarity only; there is no reranker or manual source selection.

## Chat Experience v2

Phase 14 keeps `POST /chat` stable and adds `POST /chat/stream` for authenticated `text/event-stream` responses. Stream events use a small application protocol: `start`, `delta`, `complete`, and `error`.

Assistant messages now persist nullable `response_metadata` JSON, so conversation history can restore citations, retrieval warnings, memory indicators, and action summaries. Assistant text renders as secure GitHub-flavored Markdown in the React UI; user text remains plain text and raw HTML execution is not enabled.

See [docs/chat-experience-v2.md](docs/chat-experience-v2.md) for the event protocol, persistence lifecycle, cancellation semantics, migration notes, and manual validation checklist.

## Testing

Run the test suite:

```bash
pytest
```

The tests use an isolated SQLite database with `APP_ENV=test` so they do not require a local PostgreSQL server.

Run frontend validation from `frontend/`:

```cmd
npm.cmd run lint
npm.cmd run build
npm.cmd run test:a11y
```

## Deployment And Operations

Phase 11 adds provider-neutral deployment artifacts without performing a live deployment:

```text
Dockerfile.backend
frontend/Dockerfile
frontend/nginx.conf
docker-compose.yml
.github/workflows/ci.yml
docs/deployment.md
```

Production-like local Compose:

```cmd
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend
docker compose down
```

Compose URLs:

```text
Frontend: http://localhost:5173
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health
Readiness: http://localhost:8000/ready
```

Alembic remains the migration workflow:

```cmd
.\.conda\python.exe -m alembic current
.\.conda\python.exe -m alembic upgrade head
.\.conda\python.exe -m alembic revision --autogenerate -m "description"
```

`docker compose down -v` deliberately deletes the local container PostgreSQL volume. Backups may contain private memories, chat history, document chunks, and embeddings; encrypt and access-control them.

See [docs/deployment.md](docs/deployment.md) for production prerequisites, environment variables, migration lifecycle, backup/restore commands, security checklist, rollback guidance, and known limitations. The application should not be marked as publicly deployed until a real deployment is completed and verified.

## Roadmap

- Identity layer with users, authentication, and user-owned data
- Knowledge layer with document ingestion, embeddings, vector search, and RAG
- Memory layer with ranking, updates, provenance, and relationship modeling
- Agent layer with specialized cooperative agents
- Expanded provider routing policies and model evaluation
- Tool/action system with permissions and audit logs
- Frontend expansion for registration, conversation history, memories, documents, tasks, and settings

## License

MIT License
