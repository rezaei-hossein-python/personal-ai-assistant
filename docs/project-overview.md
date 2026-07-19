# Project Overview

## Purpose

Personal AI Assistant is being developed into a modular personal AI operating system. The current phase adds user identity and authenticated access before document knowledge, agents, tools, and a React frontend.

## Current Backend

- FastAPI application in `app/main.py`
- Routers for health, authentication, chat, and memories
- SQLAlchemy models for users, conversations, messages, and memories
- Alembic migrations for database schema management
- PostgreSQL as the expected runtime database
- JWT bearer-token authentication
- User-owned conversations and memories
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
  call OpenAI
  save assistant message
  return response
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

- Document ingestion and vector search
- Richer long-term memory modeling
- Multi-model routing
- Agent orchestration
- Approved tool/action execution
- React interface
