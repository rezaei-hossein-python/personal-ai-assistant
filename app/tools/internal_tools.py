from pydantic import BaseModel, Field

from app.models.memory import Memory
from app.services.conversation_service import list_conversations
from app.services.document_service import list_documents
from app.services.memory_service import delete_memory, get_memories, save_memory
from app.services.retrieval_service import (
    VectorSearchUnavailableError,
    retrieve_relevant_chunks,
)
from app.tools.types import ToolContext, ToolDefinition, ToolError, ToolResult


class EmptyInput(BaseModel):
    pass


class SaveMemoryInput(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1)


class DeleteMemoryInput(BaseModel):
    memory_id: int | None = Field(default=None, gt=0)
    key: str | None = Field(default=None, min_length=1, max_length=100)


class SearchKnowledgeInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


def execute_list_memories(context: ToolContext, _: EmptyInput) -> ToolResult:
    memories = get_memories(context.db, context.user_id)
    return ToolResult(
        status="success",
        summary="Listed memories",
        data={
            "memories": [
                {
                    "id": memory.id,
                    "category": memory.category,
                    "key": memory.key,
                    "value": memory.value,
                }
                for memory in memories
            ],
            "count": len(memories),
        },
    )


def execute_save_memory(context: ToolContext, arguments: SaveMemoryInput) -> ToolResult:
    memory = save_memory(
        db=context.db,
        user_id=context.user_id,
        category=arguments.category,
        key=arguments.key,
        value=arguments.value,
    )
    return ToolResult(
        status="success",
        summary="Saved to memory",
        data={
            "memory": _serialize_memory(memory),
        },
    )


def execute_delete_memory(context: ToolContext, arguments: DeleteMemoryInput) -> ToolResult:
    if arguments.memory_id is None and arguments.key is None:
        raise ToolError(
            code="missing_identifier",
            message="A memory id or key is required.",
        )

    memory_id = arguments.memory_id
    if memory_id is None and arguments.key is not None:
        memory = (
            context.db.query(Memory)
            .filter(
                Memory.user_id == context.user_id,
                Memory.key == arguments.key,
            )
            .first()
        )
        if memory is None:
            raise ToolError(
                code="memory_not_found",
                message="Memory not found.",
            )
        memory_id = memory.id

    deleted = delete_memory(
        db=context.db,
        memory_id=memory_id,
        user_id=context.user_id,
    )
    if not deleted:
        raise ToolError(
            code="memory_not_found",
            message="Memory not found.",
        )

    return ToolResult(
        status="success",
        summary="Deleted memory",
        data={
            "memory_id": memory_id,
        },
    )


def execute_list_documents(context: ToolContext, _: EmptyInput) -> ToolResult:
    documents = list_documents(context.db, context.user_id)
    return ToolResult(
        status="success",
        summary="Listed documents",
        data={
            "documents": [
                {
                    "id": document.id,
                    "original_filename": document.original_filename,
                    "content_type": document.content_type,
                    "file_size": document.file_size,
                    "processing_status": document.processing_status,
                    "uploaded_at": (
                        document.uploaded_at.isoformat()
                        if document.uploaded_at
                        else None
                    ),
                }
                for document in documents
            ],
            "count": len(documents),
        },
    )


def execute_search_knowledge(
    context: ToolContext,
    arguments: SearchKnowledgeInput,
) -> ToolResult:
    try:
        chunks = retrieve_relevant_chunks(
            db=context.db,
            user_id=context.user_id,
            query=arguments.query,
            limit=arguments.limit,
            embedding_provider=context.embedding_provider,
        )
    except VectorSearchUnavailableError as exc:
        return ToolResult(
            status="error",
            summary="Knowledge search unavailable",
            error={
                "code": "knowledge_search_unavailable",
                "message": str(exc),
            },
        )

    return ToolResult(
        status="success",
        summary="Searched knowledge",
        data={
            "results": [
                {
                    "document_id": chunk.document_id,
                    "document_name": chunk.document_name,
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "start_character": chunk.start_character,
                    "end_character": chunk.end_character,
                    "distance": chunk.distance,
                }
                for chunk in chunks
            ],
            "count": len(chunks),
        },
    )


def execute_list_conversations(context: ToolContext, _: EmptyInput) -> ToolResult:
    conversations = list_conversations(context.db, context.user_id)
    return ToolResult(
        status="success",
        summary="Listed conversations",
        data={
            "conversations": [
                {
                    "conversation_id": conversation.conversation_id,
                    "title": conversation.title,
                    "created_at": (
                        conversation.created_at.isoformat()
                        if conversation.created_at
                        else None
                    ),
                    "message_count": len(conversation.messages),
                }
                for conversation in conversations
            ],
            "count": len(conversations),
        },
    )


def _serialize_memory(memory: Memory) -> dict:
    return {
        "id": memory.id,
        "category": memory.category,
        "key": memory.key,
        "value": memory.value,
    }


INTERNAL_TOOLS = [
    ToolDefinition(
        name="list_memories",
        description="Return the current user's saved memories.",
        input_model=EmptyInput,
        execute=execute_list_memories,
    ),
    ToolDefinition(
        name="save_memory",
        description="Save an explicit user-requested memory.",
        input_model=SaveMemoryInput,
        execute=execute_save_memory,
    ),
    ToolDefinition(
        name="delete_memory",
        description="Delete one of the current user's saved memories.",
        input_model=DeleteMemoryInput,
        execute=execute_delete_memory,
        destructive=True,
    ),
    ToolDefinition(
        name="list_documents",
        description="Return the current user's documents.",
        input_model=EmptyInput,
        execute=execute_list_documents,
    ),
    ToolDefinition(
        name="search_knowledge",
        description="Search the current user's document knowledge.",
        input_model=SearchKnowledgeInput,
        execute=execute_search_knowledge,
    ),
    ToolDefinition(
        name="list_conversations",
        description="Return the current user's conversation history.",
        input_model=EmptyInput,
        execute=execute_list_conversations,
    ),
]
