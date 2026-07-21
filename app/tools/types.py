from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.embedding_service import EmbeddingProvider


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class ToolContext:
    db: Session
    user_id: int
    embedding_provider: EmbeddingProvider


@dataclass
class ToolResult:
    status: str
    summary: str
    data: dict = field(default_factory=dict)
    error: dict | None = None


@dataclass
class ToolExecutionRecord:
    name: str
    status: str
    summary: str
    error: dict | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    execute: Callable[[ToolContext, BaseModel], ToolResult]
    destructive: bool = False
