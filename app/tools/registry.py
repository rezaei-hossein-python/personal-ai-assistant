from pydantic import ValidationError

from app.core.logging import logger
from app.tools.internal_tools import INTERNAL_TOOLS
from app.tools.types import (
    ToolContext,
    ToolDefinition,
    ToolError,
    ToolExecutionRecord,
    ToolResult,
)


class ToolRegistry:
    def __init__(
        self,
        tools: list[ToolDefinition],
        allowed_tools: set[str] | None = None,
        max_executions: int = 1,
    ):
        self._tools = {tool.name: tool for tool in tools}
        self.allowed_tools = allowed_tools or set(self._tools)
        self.max_executions = max_executions

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> ToolDefinition | None:
        if name not in self.allowed_tools:
            return None

        return self._tools.get(name)

    def execute(
        self,
        context: ToolContext,
        name: str,
        arguments: dict,
    ) -> tuple[ToolResult, ToolExecutionRecord]:
        tool = self.get(name)
        if tool is None:
            logger.warning("Tool blocked name=%s user_id=%s", name, context.user_id)
            result = ToolResult(
                status="error",
                summary="Tool is not allowed.",
                error={
                    "code": "tool_not_allowed",
                    "message": "Tool is not allowed.",
                },
            )
            return result, _record(name, result)

        try:
            validated_arguments = tool.input_model(**arguments)
            result = tool.execute(context, validated_arguments)
        except ValidationError as exc:
            result = ToolResult(
                status="error",
                summary="Tool arguments were invalid.",
                error={
                    "code": "invalid_arguments",
                    "message": _validation_message(exc),
                },
            )
        except ToolError as exc:
            result = ToolResult(
                status="error",
                summary=exc.message,
                error={
                    "code": exc.code,
                    "message": exc.message,
                },
            )
        except Exception:
            logger.exception("Tool execution failed name=%s user_id=%s", name, context.user_id)
            result = ToolResult(
                status="error",
                summary="Tool execution failed.",
                error={
                    "code": "execution_failed",
                    "message": "Tool execution failed.",
                },
            )

        logger.info(
            "Tool execution completed name=%s user_id=%s status=%s",
            name,
            context.user_id,
            result.status,
        )
        return result, _record(name, result)


def build_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=INTERNAL_TOOLS,
        allowed_tools={
            "list_memories",
            "save_memory",
            "delete_memory",
            "list_documents",
            "search_knowledge",
            "list_conversations",
        },
        max_executions=1,
    )


def _record(name: str, result: ToolResult) -> ToolExecutionRecord:
    return ToolExecutionRecord(
        name=name,
        status=result.status,
        summary=result.summary,
        error=result.error,
    )


def _validation_message(exc: ValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first_error.get("loc", []))
    message = first_error.get("msg", "Invalid arguments")
    return f"{location}: {message}" if location else message
