# Personal AI Assistant

## Overview

Personal AI Assistant is an early-stage FastAPI backend for a modular personal AI operating system. The current system supports chat, message history, long-term memory extraction, and memory management.

## Current Architecture

```text
FastAPI
  app/main.py
    /health
    /chat
    /memories

Routers
  app/routers/chat.py
  app/routers/memories.py
  app/routers/health.py

Services
  OpenAI response generation
  Memory extraction
  Conversation/message persistence
  Memory CRUD

Database
  PostgreSQL
  SQLAlchemy ORM
  Alembic migrations

Models
  Conversation
  Message
  Memory
```

## Requirements

- Python 3.12+
- PostgreSQL
- OpenAI API key

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
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/personal_ai
```

PostgreSQL is the expected database. SQLite is only supported for tests with `APP_ENV=test`.

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
- Multi-model routing for OpenAI, Gemini, Claude, and Grok
- Tool/action system with permissions and audit logs
- React frontend for chat, memories, documents, tasks, and settings

## License

MIT License
