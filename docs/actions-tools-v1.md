# Actions & Tools v1

Actions & Tools v1 adds a small internal action framework to the chat
orchestrator. It is intentionally bounded: tools only call existing application
services, run under the authenticated user's scope, and do not expose arbitrary
code, SQL, filesystem, or external integration access.

## Architecture

The framework lives under `app/tools`.

- `ToolDefinition` declares a unique name, description, Pydantic input model,
  execution function, and whether the tool is destructive.
- `ToolRegistry` stores the allowlist, validates input, executes tools, catches
  errors, and returns structured results.
- `ToolContext` carries the current database session, authenticated `user_id`,
  and embedding provider into tool execution.
- `ActionAgent` performs deterministic v1 tool selection from user text.
- `ChatOrchestrator` executes selected tools, adds safe tool metadata to the
  response, and makes tool results available to response generation.

Native provider function calling is not used in v1 because the current provider
abstraction only exposes plain generation and structured generation. The v1
strategy is deterministic planning for a small internal tool set.

## Available Tools

- `list_memories`: returns the current user's saved memories.
- `save_memory`: saves an explicit user-requested memory.
- `delete_memory`: deletes one current-user memory by id or key.
- `list_documents`: returns the current user's uploaded documents.
- `search_knowledge`: searches the current user's document chunks through the
  existing retrieval service.
- `list_conversations`: returns the current user's conversation history.

## Execution Lifecycle

1. The planner determines normal Memory and Knowledge retrieval intent.
2. The action agent deterministically selects zero or more candidate actions.
3. The orchestrator enforces explicit retrieval overrides. For example,
   `knowledge_retrieval: false` blocks `search_knowledge`.
4. The registry checks the allowlist and validates arguments with each tool's
   input model.
5. At most one tool is executed per chat request.
6. The tool returns a `ToolResult` containing status, summary, data, and optional
   structured error.
7. The orchestrator adds sanitized `metadata.actions` entries to the chat
   response and persists the assistant message content as before.

## Safety Boundaries

- User isolation is enforced by passing only the authenticated `user_id` into
  tool context and reusing existing scoped services.
- Only registered allowlisted tools can execute.
- Inputs are validated by Pydantic before tool functions run.
- The execution limit is one tool per request.
- There is no recursive tool loop.
- There is no arbitrary shell execution.
- There is no arbitrary SQL execution.
- There is no arbitrary filesystem access.
- External services such as Gmail and Google Calendar are intentionally absent.

## Destructive Actions

`delete_memory` is marked destructive and is only selected from clear user
phrases such as "delete", "remove", or "forget" plus a memory-related target.
The chat path does not delete memories for ordinary lookup questions like
"What do you remember about my editor?"

## API Metadata

The `/chat` request body is unchanged. The response metadata adds an optional
backward-compatible field:

```json
{
  "metadata": {
    "actions": [
      {
        "tool_name": "save_memory",
        "status": "success",
        "summary": "Saved to memory"
      }
    ]
  }
}
```

The metadata is intentionally minimal and user-facing. Internal stack traces,
database details, raw validation internals, and private implementation details
are not returned.

## Frontend

Assistant messages render subtle action badges such as "Saved to memory",
"Searched knowledge", and "Listed documents". Memory-changing tool results
trigger a refresh of the Memory UI.

## Compatibility Notes

Knowledge/RAG v1, Memory v1, and Conversation History v1 are preserved. Tool
created memories use the existing memory service, so they appear in the Memory
UI and persist across sessions.

Historical messages do not currently persist tool metadata because the existing
message schema stores only role, content, timestamps, ownership, and
conversation ids. Adding persisted tool metadata would require a schema
migration and is deferred.

## Future Integrations

External tools can be added later by registering new `ToolDefinition` instances
with narrow input schemas, explicit allowlisting, user-scoped credentials, and
tool-specific safety policies. Gmail, Google Calendar, and other third-party
actions should remain separate from this internal v1 framework until their auth,
confirmation, and audit requirements are designed.
