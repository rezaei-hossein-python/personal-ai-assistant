from dataclasses import dataclass, field
from enum import Enum

from app.services.retrieval_service import RetrievedChunk


class Intent(str, Enum):
    GENERAL_CHAT = "general_chat"
    MEMORY_LOOKUP = "memory_lookup"
    KNOWLEDGE_SEARCH = "knowledge_search"
    COMBINED_CONTEXT = "combined_context"


@dataclass
class Plan:
    intent: Intent
    use_memory: bool
    use_knowledge: bool
    allow_actions: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryContext:
    memories: list
    metadata: dict


@dataclass
class KnowledgeContext:
    chunks: list[RetrievedChunk]
    metadata: dict


@dataclass
class ActionResult:
    actions: list
    metadata: dict


@dataclass
class EvaluationResult:
    warnings: list[str]
    metadata: dict


@dataclass
class AgentExecutionMetadata:
    selected_intent: str
    agents_invoked: list[str]
    retrieval_count: int
    provider: str
    model: str
    evaluation_warnings: list[str]
    selected_provider: str = ""
    selected_model: str = ""
    preferred_provider: str = ""
    fallback_events: list[dict] = field(default_factory=list)
    providers_invoked: list[str] = field(default_factory=list)
    collaboration_mode_used: bool = False
