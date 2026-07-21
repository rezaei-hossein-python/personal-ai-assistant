# Deployment Guide

## Architecture Overview

Personal AI Assistant deploys as three portable services:

- FastAPI backend served by Uvicorn.
- React/Vite static frontend served by nginx with SPA fallback.
- PostgreSQL with the pgvector extension for document embeddings.

Alembic owns schema migrations. Uploaded original files are not persisted; the database stores document metadata, extracted chunks, and embeddings.

## Production Prerequisites

- Python 3.12 compatible runtime for the backend.
- Node.js 24 for frontend builds.
- PostgreSQL 16 or compatible managed PostgreSQL.
- pgvector installed and available to the application database.
- OpenAI API key for default chat and embeddings.
- TLS termination at the platform/load balancer/reverse proxy.

## Required Environment Variables

Backend:

```text
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
JWT_SECRET_KEY=at-least-32-random-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_ORIGINS=https://your-frontend.example.com
TRUSTED_HOSTS=your-api.example.com
LOG_LEVEL=INFO
MAX_UPLOAD_BYTES=10485760
API_DOCS_ENABLED=false
```

Frontend:

```text
VITE_API_BASE_URL=https://your-api.example.com
```

Do not put confidential values in `VITE_` variables because they are bundled into browser assets.

## Secret Generation

Generate `JWT_SECRET_KEY` with a cryptographically secure random source. Example:

```cmd
.\.conda\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store secrets only in the deployment platform secret manager or local untracked `.env` files.

## Database And pgvector

The migrations include `CREATE EXTENSION IF NOT EXISTS vector` for PostgreSQL. Some managed providers require enabling pgvector through their dashboard or an admin connection first. Use a least-privilege application user after setup.

## Migrations

Check current revision:

```cmd
.\.conda\python.exe -m alembic current
```

Upgrade:

```cmd
.\.conda\python.exe -m alembic upgrade head
```

Create a future migration:

```cmd
.\.conda\python.exe -m alembic revision --autogenerate -m "description"
```

Review generated migrations before applying them. Do not run destructive downgrades against production data without a tested backup.

## Backend Build And Startup

Install dependencies:

```cmd
.\.conda\python.exe -m pip install -r requirements.txt
```

Run migrations once:

```cmd
.\.conda\python.exe -m alembic upgrade head
```

Start:

```cmd
.\.conda\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Startup validates configuration, waits for the database with bounded retries, then exposes the API.

## Frontend Build And Serving

```cmd
cd frontend
npm.cmd ci
npm.cmd run build
```

Serve `frontend/dist` with a static web server. If using client-side routes, configure fallback to `index.html`. The included nginx Docker image also proxies `/api` to the backend in Compose.

## Docker Compose Workflow

Production-like local URLs:

```text
Frontend: http://localhost:5173
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health
Readiness: http://localhost:8000/ready
```

Commands:

```cmd
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend
docker compose down
```

Delete local container database data only when intended:

```cmd
docker compose down -v
```

This deletes the named PostgreSQL volume and all local container database data.

## Health Checks

- `/health`: liveness, confirms the process is running.
- `/ready`: readiness, confirms required services such as the database are reachable.

Neither endpoint exposes secrets or database credentials.

## Logs And Troubleshooting

Logs include timestamp, level, logger, request ID, method, route, status, and duration. Server exceptions are logged. User-facing production errors return safe generic messages.

Check:

```cmd
docker compose logs -f backend
docker compose logs -f migrate
docker compose logs -f db
```

## Backup And Restore

Backups may contain private user data, memories, chat history, document chunks, and embeddings. Encrypt backup files and restrict access.

Backup:

```cmd
pg_dump --format=custom --file=personal_ai.backup "$env:DATABASE_URL"
```

Restore to an empty database:

```cmd
pg_restore --dbname "$env:DATABASE_URL" --clean --if-exists personal_ai.backup
```

Plain SQL alternative:

```cmd
pg_dump --file=personal_ai.sql "$env:DATABASE_URL"
psql "$env:DATABASE_URL" -f personal_ai.sql
```

Restoring into the wrong database can overwrite data. Database deletion is destructive.

## Uploaded-File Persistence

Original uploaded files are not stored. Container-local filesystem storage is not part of the persistence model. The database stores metadata, extracted chunks, and embeddings. Reconstructing the original document from the database is not supported.

## CORS And Public URLs

Set `ALLOWED_ORIGINS` to the exact frontend origins. Do not use `*` with credentials. Set `TRUSTED_HOSTS` to the public API hostnames used by browsers or reverse proxies.

## OpenAI Cost Considerations

Document upload embeds each chunk and chat may call generation plus query embeddings. Costs scale with uploaded document size, chunk count, chat volume, and selected models. Monitor usage in the OpenAI dashboard and set billing limits.

## Security Checklist

- Use a strong `JWT_SECRET_KEY`.
- Keep `DEBUG=false` and `API_DOCS_ENABLED=false` in production.
- Use HTTPS.
- Restrict CORS and trusted hosts.
- Keep `.env` files out of Git.
- Apply migrations before app startup.
- Back up PostgreSQL before schema changes.
- Use least-privilege database credentials.
- Review logs for accidental sensitive content before sharing them.

## Rollback Strategy

Keep the previous backend image, frontend image/static bundle, and database backup for each release. To roll back application code, redeploy the previous images. Database rollbacks require a tested restore plan; do not rely on Alembic downgrades for production recovery.

## Provider-Neutral Deployment Sequence

1. Provision PostgreSQL and pgvector.
2. Create database/user and store `DATABASE_URL` as a secret.
3. Store model provider keys and `JWT_SECRET_KEY` as secrets.
4. Build backend and frontend artifacts.
5. Run `alembic upgrade head` once.
6. Start backend.
7. Start frontend/static server.
8. Configure DNS/TLS/reverse proxy.
9. Verify `/health`, `/ready`, login, chat, uploads, memory, history, tools, and knowledge search.

## Managed Platform Notes

- Render/Railway/Fly.io: run Alembic as a release/predeploy command, then start the backend web process.
- Azure/AWS/Google Cloud: use managed PostgreSQL where pgvector is supported, store secrets in the platform secret manager, and serve the frontend from static hosting or the provided nginx image.

No provider deployment has been performed or verified in Phase 11.

## Known Limitations

- No live public deployment has been completed.
- Original uploaded files are not retained.
- Tokens are stored in browser local storage for refresh persistence; this is convenient but exposed to XSS if unsafe rendering is introduced later.
- There is no server-side token revocation list; logout is client-side cleanup.
- API docs should be disabled for production even though Compose keeps them enabled for local inspection.
