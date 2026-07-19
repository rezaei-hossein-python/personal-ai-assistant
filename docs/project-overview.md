# Project Overview

## Purpose

Personal AI Assistant is being developed into a modular personal AI operating system. The current phase adds user-owned document ingestion, chunking, and a retrieval-ready RAG foundation before agents, tools, and a React frontend.

## Current Backend

- FastAPI application in `app/main.py`
- Routers for health, authentication, chat, memories, and documents
- SQLAlchemy models for users, conversations, messages, memories, documents, and document chunks
- Alembic migrations for database schema management
- PostgreSQL as the expected runtime database
- pgvector-backed semantic document search
- JWT bearer-token authentication
- User-owned conversations, memories, and documents
- PDF, DOCX, TXT, and Markdown text extraction
- Reusable text chunking with OpenAI embeddings stored as pgvector vectors
- OpenAI Responses API integration for chat and memory extraction

## Current Request Flow

```text
POST /chat
  verify bearer token
  load current user
  create or load conversation
  save user message
  extract possible memory
  save or update memory
  load message history
  load user memories
  retrieve relevant user document chunks with pgvector cosine search
  call OpenAI
  save assistant message
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

- embedding backfill for documents uploaded before Phase 3.1
- Richer long-term memory modeling
- Multi-model routing
- Agent orchestration
- Approved tool/action execution
- React interface
