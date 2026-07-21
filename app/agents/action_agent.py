import re

from app.agents.types import ActionRequest, ActionResult, Plan
from app.tools import ToolRegistry, build_default_tool_registry


class ActionAgent:
    name = "ActionAgent"

    def __init__(self, tool_registry: ToolRegistry | None = None):
        self.tool_registry = tool_registry or build_default_tool_registry()

    def prepare_actions(
        self,
        plan: Plan,
        message: str = "",
    ) -> ActionResult:
        actions = self.select_actions(message)
        plan.allow_actions = bool(actions)
        return ActionResult(
            actions=actions,
            metadata={
                "enabled": bool(actions),
                "supported_actions": self.tool_registry.tool_names,
                "max_executions": self.tool_registry.max_executions,
            },
        )

    def select_actions(self, message: str) -> list[ActionRequest]:
        lowered = _normalize(message)

        save_memory_arguments = _extract_save_memory_arguments(message)
        if save_memory_arguments is not None:
            return [
                ActionRequest(
                    tool_name="save_memory",
                    arguments=save_memory_arguments,
                    explicit_intent=True,
                )
            ]

        delete_memory_arguments = _extract_delete_memory_arguments(message)
        if delete_memory_arguments is not None:
            return [
                ActionRequest(
                    tool_name="delete_memory",
                    arguments=delete_memory_arguments,
                    explicit_intent=True,
                )
            ]

        if _is_list_conversations_request(lowered):
            return [ActionRequest(tool_name="list_conversations", arguments={})]

        if _is_list_documents_request(lowered):
            return [ActionRequest(tool_name="list_documents", arguments={})]

        search_query = _extract_knowledge_search_query(message)
        if search_query is not None:
            return [
                ActionRequest(
                    tool_name="search_knowledge",
                    arguments={"query": search_query},
                )
            ]

        if _is_list_memories_request(lowered):
            return [ActionRequest(tool_name="list_memories", arguments={})]

        return []


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.lower()).strip()


def _extract_save_memory_arguments(message: str) -> dict | None:
    normalized = _normalize(message).rstrip(".!?")
    if not re.search(r"\b(remember|save|store|note)\b", normalized):
        return None

    text = re.sub(
        r"^(please\s+)?(remember|save|store|note)(\s+that)?\s+",
        "",
        normalized,
        count=1,
    )
    text = re.sub(r"^(my|that my|the)\s+", "my ", text, count=1)

    match = re.match(r"my\s+(.+?)\s+(?:is|=)\s+(.+)$", text)
    if not match:
        match = re.match(r"(.+?)\s+(?:is|=)\s+(.+)$", text)
    if not match:
        return None

    key = _key_from_text(match.group(1))
    value = match.group(2).strip(" .")
    if not key or not value:
        return None

    return {
        "category": "preference" if "favorite" in key or "prefer" in key else "profile",
        "key": key,
        "value": value,
    }


def _extract_delete_memory_arguments(message: str) -> dict | None:
    normalized = _normalize(message).rstrip(".!?")
    if not re.search(r"\b(delete|remove|forget)\b", normalized):
        return None
    if not re.search(r"\b(memory|remember|preference|that)\b", normalized):
        return None

    id_match = re.search(r"\bmemory\s+#?(\d+)\b", normalized)
    if id_match:
        return {"memory_id": int(id_match.group(1))}

    key_match = re.search(r"\b(?:about|for)\s+(?:my\s+)?(.+)$", normalized)
    if key_match:
        key = _key_from_text(key_match.group(1))
        return {"key": key} if key else None

    return None


def _extract_knowledge_search_query(message: str) -> str | None:
    normalized = _normalize(message).rstrip(".!?")
    if not re.search(r"\b(search|find|look up)\b", normalized):
        return None
    if not re.search(r"\b(document|documents|file|files|knowledge|notes)\b", normalized):
        return None

    patterns = [
        r"\b(?:search|find|look up)\s+(?:my\s+)?(?:documents|files|knowledge|notes)\s+for\s+(.+)$",
        r"\b(?:search|find|look up)\s+(.+?)\s+in\s+(?:my\s+)?(?:documents|files|knowledge|notes)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            query = match.group(1).strip(" .")
            return query or None

    return message.strip()


def _is_list_documents_request(lowered: str) -> bool:
    return bool(
        re.search(r"\b(what|which|list|show)\b", lowered)
        and re.search(r"\b(documents|files)\b", lowered)
        and re.search(r"\b(have|uploaded|list|show)\b", lowered)
    )


def _is_list_conversations_request(lowered: str) -> bool:
    return bool(
        re.search(r"\b(what|which|list|show)\b", lowered)
        and (
            re.search(r"\b(conversations|chats)\b", lowered)
            or re.search(r"\bconversation history\b", lowered)
        )
        and re.search(r"\b(have|list|show|history)\b", lowered)
    )


def _is_list_memories_request(lowered: str) -> bool:
    return bool(
        re.search(r"\b(what|which|list|show)\b", lowered)
        and re.search(r"\b(memories|memory|remember)\b", lowered)
        and re.search(r"\b(have|saved|stored|list|show)\b", lowered)
    )


def _key_from_text(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    normalized = re.sub(r"_+", "_", normalized)
    return normalized[:100]
