from app.agents.types import Intent, Plan
import re


class PlannerAgent:
    name = "PlannerAgent"

    MEMORY_TERMS = {
        "remember",
        "memory",
        "preference",
        "preferences",
        "prefer",
        "me",
    }
    KNOWLEDGE_TERMS = {
        "document",
        "documents",
        "notes",
        "file",
        "knowledge",
        "search",
        "according",
    }

    def plan(self, message: str) -> Plan:
        lowered = message.lower()
        tokens = set(re.findall(r"\b\w+\b", lowered))
        use_memory = bool(tokens & self.MEMORY_TERMS)
        use_knowledge = bool(tokens & self.KNOWLEDGE_TERMS)

        if use_memory and use_knowledge:
            intent = Intent.COMBINED_CONTEXT
        elif use_memory:
            intent = Intent.MEMORY_LOOKUP
        elif use_knowledge:
            intent = Intent.KNOWLEDGE_SEARCH
        else:
            intent = Intent.GENERAL_CHAT

        return Plan(
            intent=intent,
            use_memory=use_memory or intent == Intent.GENERAL_CHAT,
            use_knowledge=use_knowledge,
            metadata={
                "routing": "deterministic_keyword",
            },
        )
