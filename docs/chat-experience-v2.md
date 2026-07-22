# Chat Experience And Metadata Persistence v2

Phase 14 adds persisted assistant-response metadata, authenticated streaming chat, and secure Markdown rendering without changing the existing `POST /chat` contract.

## Endpoints

`POST /chat` remains the compatibility endpoint. `POST /chat/stream` accepts the same request shape, requires the same bearer token, enforces the same authenticated user ownership rules, and returns `text/event-stream`.

## Streaming Event Protocol

Each event has an SSE event name and JSON data payload:

```text
event: start
data: {"conversation_id":"..."}

event: delta
data: {"text":"partial assistant text"}

event: complete
data: {"response":"complete assistant text","conversation_id":"...","metadata":{...}}

event: error
data: {"message":"safe user-facing error"}
```

The frontend treats `complete` as authoritative. Delta text is visible while the request is in flight, but the final assistant message and metadata are only considered saved after `complete`.

## Persistence Lifecycle

The `messages` table has a nullable `response_metadata` JSON column. It is intentionally not named `metadata` because SQLAlchemy reserves that attribute name.

The user message follows the existing conversation persistence behavior. The assistant message is saved only after orchestration, provider generation, evaluation, and metadata construction complete successfully. Failed streams and interrupted streams do not save a completed assistant message. Legacy rows with `NULL` metadata remain valid and serialize as `response_metadata: null`.

The JSON column is compatible with PostgreSQL server mode and SQLite test/desktop mode. PostgreSQL with pgvector remains the server retrieval path; desktop SQLite mode keeps its existing local behavior.

## Historical Metadata

Historical assistant messages return `response_metadata` using the same structured shape as live chat metadata:

- `knowledge`: retrieval enabled state, mode, count, source citation summaries, and warning
- `memory`: retrieval enabled state, mode, count, and category/key summaries
- `actions`: tool name, status, and safe summary

The API only retrieves conversations through the authenticated user's ownership filter. Provider secrets, credentials, raw stack traces, and internal database identifiers unrelated to citations are not exposed.

## Markdown Security

Assistant messages render with `react-markdown` and `remark-gfm`. Raw HTML rendering is not enabled, so HTML such as `<script>` is rendered as inert text instead of executed. Links are rendered with `target="_blank"` and `rel="noreferrer noopener"`.

User messages remain plain text. Markdown styles keep code blocks and tables scrollable inside the message bubble so narrow viewports and 200% zoom do not force page-wide overflow.

## Cancellation And Failure Semantics

The React client uses authenticated `fetch`, incremental SSE parsing, and `AbortController`. Stop generating aborts the request, preserves visible partial text, marks the assistant message as incomplete, clears busy state, and restores focus to the message input. The client does not automatically retry through `POST /chat`, because that could duplicate persisted user messages.

Server errors emit a safe `error` event when possible and roll back unfinished assistant writes. Client disconnects are handled without exposing provider internals.

## Manual Validation

Backend:

```cmd
uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

Frontend:

```cmd
cd frontend
npm.cmd run dev
```

Frontend URL: `http://localhost:5173`

Checklist:

- Sign in.
- Send a prompt that produces several paragraphs and confirm progressive text.
- Confirm only one assistant bubble is created during streaming.
- Confirm final metadata appears after completion.
- Refresh or sign in again, reopen the conversation, and confirm Markdown plus metadata return from history.
- Test headings, lists, links, inline code, fenced code blocks, and tables.
- Confirm raw HTML does not execute.
- Start a response, activate Stop generating, and confirm partial text remains marked incomplete.
- Test keyboard-only operation and Windows Narrator announcements for start, completion, cancellation, Markdown links/headings, citations, and memory metadata.
- Run `.\.conda\python.exe -m desktop.main` and repeat core streaming, Markdown, cancellation, and history checks in the desktop window.

## Validation Commands

```cmd
pytest
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run test:a11y
```

Migration checks:

```cmd
.\.conda\python.exe -m alembic upgrade head
.\.conda\python.exe -m alembic current
```

## Known Limitations

- OpenAI has native incremental streaming; other providers currently use the provider-neutral fallback stream around their existing full-response generation.
- Provider-routing details are kept in backend execution metadata unless a safe user-facing UI explicitly needs them.
- Document citations identify document and chunk locations but do not open an in-document preview.
- Formal WCAG certification has not been performed.
