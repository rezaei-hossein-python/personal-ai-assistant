# Personal AI Assistant

## Overview

Personal AI Assistant is an early-stage FastAPI backend for a modular personal AI operating system. The current system supports authenticated chat, message history, long-term memory extraction, memory management, document ingestion, RAG, lightweight agent orchestration, and deterministic multi-model provider routing.

## Current Architecture

```text
FastAPI
  app/main.py
    /health
    /auth/register
    /auth/login
    /chat
    /memories
    /documents

Routers
  app/routers/auth.py
  app/routers/chat.py
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
  Memory extraction
  Document parsing and chunking
  Retrieval/RAG prompt context
  Conversation/message persistence
  Memory and document CRUD

Database
  PostgreSQL
  pgvector required for semantic search
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

## Requirements

- Python 3.12+
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

PostgreSQL is the expected database. SQLite is only supported for tests with `APP_ENV=test`.

Semantic document search requires PostgreSQL with the `vector` extension available. Phase 3.1 enables pgvector-backed storage with `document_chunks.embedding vector(1536)` and cosine similarity retrieval.

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

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
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

## Documents And RAG

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

RAG architecture:

```text
Authenticated chat request
  ChatOrchestrator
    PlannerAgent selects intent/capabilities
    MemoryAgent loads relevant user memories
    KnowledgeAgent retrieves user-owned document chunks
    ActionAgent reserves a safe no-op action interface
    ModelRouter selects a configured ModelProvider
    ModelProvider generates a response
    EvaluatorAgent records obvious context warnings
```

Document chunk metadata keeps source document and chunk identifiers so later frontend citations can point back to the relevant source.

Documents uploaded after Phase 3.1 receive embeddings during ingestion. Documents uploaded before the embedding column existed may need to be re-uploaded or backfilled before they appear in semantic search results.

Backfill missing chunk embeddings:

```bash
python scripts/backfill_embeddings.py
```

The backfill command is idempotent: it skips chunks that already have embeddings and reports scanned, updated, skipped, and failed counts.

## Testing

Run the test suite:

```bash
pytest
```

The tests use an isolated SQLite database with `APP_ENV=test` so they do not require a local PostgreSQL server.

## Roadmap

- Identity layer with users, authentication, and user-owned data
- Knowledge layer with document ingestion, embeddings, vector search, and RAG
- Memory layer with ranking, updates, provenance, and relationship modeling
- Agent layer with specialized cooperative agents
- Expanded provider routing policies and model evaluation
- Tool/action system with permissions and audit logs
- React frontend for chat, memories, documents, tasks, and settings

## License

MIT License
