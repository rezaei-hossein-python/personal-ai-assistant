from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    knowledge_retrieval: bool | None = None


class KnowledgeSource(BaseModel):
    document_id: int
    document_name: str
    chunk_id: int
    chunk_index: int
    start_character: int | None = None
    end_character: int | None = None
    distance: float | None = None


class KnowledgeRetrievalMetadata(BaseModel):
    enabled: bool
    mode: Literal["planner", "explicit_enabled", "explicit_disabled"]
    retrieval_count: int
    sources: list[KnowledgeSource] = Field(default_factory=list)
    warning: str | None = None


class ChatResponseMetadata(BaseModel):
    knowledge: KnowledgeRetrievalMetadata | None = None


class ChatResponse(BaseModel):
    response: str
    metadata: ChatResponseMetadata | None = None
