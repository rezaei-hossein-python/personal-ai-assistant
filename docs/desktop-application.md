# Desktop Application Guide

## Architecture Overview

Desktop Application v1 packages the existing React/Vite frontend and FastAPI backend into a Windows-focused local desktop app. The executable starts a private FastAPI process in a background thread, serves the compiled React bundle from the same loopback origin, opens a native `pywebview` window, and stops the backend when the window closes.

Desktop v1 keeps the existing browser/cloud architecture intact. PostgreSQL, pgvector, Alembic, Docker, and browser development mode remain available.

## Audit Findings

Reusable directly:

- FastAPI entry point, routers, authentication, chat orchestration, memories, conversations, documents, tools, and safe error handling.
- React/Vite frontend and centralized `/api` API client.
- SQLAlchemy models and service logic.
- Existing SQLite-compatible model variants for document chunk embeddings.
- Existing Python cosine retrieval path used when the SQLAlchemy dialect is SQLite.

Desktop adapters added:

- `desktop/` launcher, paths, settings, secrets, and lifecycle modules.
- Desktop-only `/api/desktop/*` status and secret endpoints.
- Desktop-only `/api/*` router aliases because Vite dev proxy strips `/api` but packaged FastAPI serves it directly.
- Desktop SQLite initialization with a schema-version table.
- FastAPI static serving for `frontend/dist`.
- Desktop settings/onboarding UI for OpenAI API key status and replacement.
- PyInstaller spec and build script.

PostgreSQL dependencies retained:

- `DATABASE_BACKEND=postgres` remains the default.
- Alembic migrations remain PostgreSQL-oriented for development and cloud deployment.
- pgvector migration and production semantic search remain unchanged.
- `psycopg2-binary` remains packaged for PostgreSQL compatibility.

pgvector dependencies:

- PostgreSQL mode stores `document_chunks.embedding` as `vector(1536)` and queries with `<=>`.
- SQLite desktop mode stores embeddings as JSON and ranks chunks with Python cosine distance.

Frontend assumptions changed for desktop:

- Packaged mode no longer needs a Vite dev server.
- Browser URL assumptions are avoided by serving the SPA from the local FastAPI origin.
- Static asset paths are served from FastAPI `/assets`.
- API requests still use `/api`, matching both Vite proxy and desktop local serving.

## Desktop Versus Browser/Cloud Modes

Desktop mode:

- Runs with `DESKTOP_MODE=true`.
- Binds only to `127.0.0.1`.
- Defaults to SQLite under `%LOCALAPPDATA%\PersonalAIAssistant`.
- Loads OpenAI API keys from Windows Credential Manager through `keyring`.
- Serves `frontend/dist` from FastAPI.
- Disables public API docs.

Browser/cloud mode:

- Uses `app.main:app` normally.
- Defaults to PostgreSQL.
- Uses Alembic migrations.
- Uses Vite dev proxy or a deployed static frontend.
- Reads deployment secrets from `.env` or platform secret management.

## System Requirements

- Windows 10 or newer.
- WebView2 runtime available on Windows.
- Internet access for OpenAI API calls.
- OpenAI API key for chat and embeddings.
- Recommended current laptop target: 8 GB RAM, 13th-generation Intel Core i5, no dedicated GPU required.

Desktop v1 does not include a local language model and is not fully offline.

## Development Prerequisites

```cmd
.\.conda\python.exe -m pip install -r requirements.txt
cd frontend
npm.cmd ci
```

## Startup Lifecycle

`.\.conda\python.exe -m desktop.main` performs:

1. Resolve `%LOCALAPPDATA%\PersonalAIAssistant`.
2. Create `data`, `database`, `logs`, `cache`, `temp`, and `backups`.
3. Load `settings.json`.
4. Load `OPENAI_API_KEY` and `JWT_SECRET_KEY` from Windows Credential Manager.
5. Select an available loopback port.
6. Set desktop environment variables.
7. Start FastAPI on `127.0.0.1`.
8. Create or verify the SQLite schema.
9. Wait for `/ready` with bounded retries.
10. Open `pywebview` at the local backend URL.
11. Stop Uvicorn when the window closes.

## Data Directory

Desktop mutable data is stored outside the installation directory:

```text
%LOCALAPPDATA%\PersonalAIAssistant
├── backups
├── cache
├── database
│   └── assistant.sqlite3
├── logs
│   ├── backend.log
│   └── desktop-launcher.log
├── temp
└── settings.json
```

This per-user location does not require administrator access and survives application upgrades.

## Secure OpenAI Key Storage

The OpenAI API key is stored through Python `keyring`, which uses Windows Credential Manager on Windows. It is not embedded in React, the executable, `.env`, logs, or API responses.

Desktop endpoints return only configured/not-configured status and a masked key. Moving data to another machine does not copy Credential Manager secrets; the key must be re-entered.

## SQLite Desktop Mode

Desktop mode sets:

```text
DATABASE_BACKEND=sqlite
DATABASE_URL=sqlite:///%LOCALAPPDATA%/PersonalAIAssistant/database/assistant.sqlite3
```

SQLite persists users, memories, conversations, messages, document metadata, document chunks, embeddings, and supported tool-related state. Foreign keys are enabled on SQLite connections.

The desktop schema is created from SQLAlchemy metadata and tracked with `desktop_schema_version`. Desktop startup does not apply PostgreSQL Alembic migrations to SQLite.

## PostgreSQL Server Mode

PostgreSQL remains the default for server, development, Docker, and cloud deployment. Continue using Alembic:

```cmd
.\.conda\python.exe -m alembic upgrade head
```

## Vector Retrieval

PostgreSQL mode uses pgvector cosine distance. Desktop SQLite mode stores embeddings as JSON and performs user-scoped Python cosine ranking in memory. This is intended for personal-scale document collections, not enterprise-scale retrieval.

Retrieval preserves document name, document ID, chunk ID, chunk index, character offsets, distance, and citation metadata.

## Building The Frontend

```cmd
cd frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run build
```

The desktop launcher requires `frontend/dist` in source mode. The PyInstaller build bundles it as `frontend_dist`.

## Running From Source

```cmd
.\.conda\python.exe -m desktop.main
```

This opens the native desktop window. No Uvicorn, npm, Docker, or browser command is required.

## Creating The Package

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_desktop.ps1
```

Output:

```text
dist\PersonalAIAssistant\PersonalAIAssistant.exe
```

The script runs `npm ci`, frontend lint/build, backend tests unless `-SkipTests` is supplied, and PyInstaller.

## Installer Strategy

Desktop v1 produces a portable one-folder Windows build. Inno Setup installer support is deferred until installer tooling and a second-machine validation pass are available.

## Logs And Troubleshooting

Logs are written under:

```text
%LOCALAPPDATA%\PersonalAIAssistant\logs
```

Logs include startup, selected port, database mode, schema initialization, readiness, safe backend errors, and shutdown. They must not include OpenAI keys, JWTs, passwords, authorization headers, complete documents, full memories, or full conversations.

## Backup

Close the application first. Back up:

- `%LOCALAPPDATA%\PersonalAIAssistant\database\assistant.sqlite3`
- `%LOCALAPPDATA%\PersonalAIAssistant\settings.json`
- Any future persisted document files if added later.

Do not include cache/temp directories unless needed for diagnostics. Do not copy OpenAI keys into backup archives.

## Restore

Close the application. Restore the backed-up files into the same relative paths under `%LOCALAPPDATA%\PersonalAIAssistant`. Re-enter the OpenAI API key on a new Windows account or machine because Credential Manager secrets are not portable files.

## Updating

Replace the portable build folder with the new build. Do not delete `%LOCALAPPDATA%\PersonalAIAssistant`. SQLite schema upgrades must preserve user data and fail clearly if an unsupported newer schema is detected.

## Uninstall

Delete the portable build folder. This does not remove user data. To remove local data manually, close the app and delete `%LOCALAPPDATA%\PersonalAIAssistant`. Remove stored credentials from Windows Credential Manager if needed.

## Privacy Model

Desktop data remains on the local Windows user profile except OpenAI API requests, which send prompts, retrieved context, and embeddings input to OpenAI. OpenAI usage may cost money. Desktop v1 is local-first, not fully offline.

## Network Behavior

Desktop backend binds only to `127.0.0.1` on an automatically selected port. It does not intentionally open a firewall rule and does not bind to `0.0.0.0`. Loopback services are local, but JWT authentication is still preserved because other local processes could make HTTP requests.

## Known Limitations

- OpenAI still requires internet access.
- OpenAI API usage may cost money.
- Desktop v1 is Windows-focused.
- Local AI models such as Ollama are not included.
- SQLite vector search is personal-scale.
- Original uploaded files are not retained by the current ingestion design; metadata, chunks, and embeddings are stored.
- No email, calendar, Word, cloud-drive, or external app integrations are included.
- No automatic background monitoring is included.
- Installer validation requires a future installer pass and ideally a second Windows machine.
- Operating-system credential storage behavior can vary by environment.

## Future Work

- Optional Ollama/local-model provider.
- Optional Inno Setup installer.
- External app integrations such as email, calendar, Word, and cloud drives.
- More robust desktop schema migrations with pre-upgrade backups once schema changes are needed.

## Manual Regression Checklist

Startup:

- Launch from source with `.\.conda\python.exe -m desktop.main`.
- Launch packaged `dist\PersonalAIAssistant\PersonalAIAssistant.exe`.
- Verify only one application instance is practical for normal use.
- Verify no manual backend command is needed.
- Verify no external browser opens.
- Close and confirm backend stops.

Secrets:

- First-run API-key prompt appears.
- Save key.
- Replace key.
- Remove key.
- Verify logs do not contain key.
- Verify frontend bundle does not contain key.

Persistence:

- Register/login through `/auth/register` API and frontend login.
- Save memory.
- Create conversation.
- Upload document.
- Close application.
- Reopen application.
- Verify data remains.

Knowledge:

- Upload TXT, Markdown, DOCX, and PDF.
- Ask grounded question.
- Verify citations.
- Verify Auto, Always, and Never.

Tools:

- Save memory naturally.
- List documents.
- Search knowledge.
- List conversations.
- Explicitly delete memory.
- Verify vague deletion request is rejected.

Security:

- Verify backend listens only on `127.0.0.1`.
- Verify invalid token is rejected.
- Verify no public network access is intended.
- Verify packaged files contain no `.env`.

Compatibility:

- Run browser development mode.
- Run PostgreSQL mode.
- Run backend tests.
- Run frontend lint.
- Run frontend build.
