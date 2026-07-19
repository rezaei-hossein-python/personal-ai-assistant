# Project Overview

## Purpose

Personal AI Assistant is being developed into a modular personal AI operating system. The current backend includes authenticated chat, user-owned memory and documents, RAG, lightweight agent orchestration, and deterministic multi-model provider routing.

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

## Current Request Flow

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
  validate file type
  extract text
  chunk text
  store document metadata
  store chunks linked to the document
```

## Local Development

1. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

2. Configure `.env`.

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

3. Run migrations.

   ```bash
   alembic upgrade head
   ```

4. Start the API.

   ```bash
   uvicorn app.main:app --reload
   ```

5. Run tests.

   ```bash
   pytest
   ```

## Architecture Direction

Future phases will add:

- richer agent tools and task execution
- Richer long-term memory modeling
- richer multi-provider model evaluation
- Approved tool/action execution
- React interface
