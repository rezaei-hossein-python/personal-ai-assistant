from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider


class VectorSearchUnavailableError(Exception):
    pass


@dataclass
class RetrievedChunk:
    document_id: int
    document_name: str
    chunk_id: int
    chunk_index: int
    content: str
    metadata: dict


def is_vector_search_available(db: Session) -> bool:
    return db.bind is not None and db.bind.dialect.name == "postgresql" and False


def retrieve_relevant_chunks(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[RetrievedChunk]:
    if not is_vector_search_available(db):
        raise VectorSearchUnavailableError(
            "Semantic retrieval requires PostgreSQL pgvector. The vector "
            "extension is not available in this environment."
        )

    provider = embedding_provider or get_embedding_provider()
    provider.embed_text(query)

    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.user_id == user_id)
        .limit(limit)
        .all()
    )

    return [
        RetrievedChunk(
            document_id=document.id,
            document_name=document.original_filename,
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            metadata=chunk.chunk_metadata or {},
        )
        for chunk, document in rows
    ]


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""

    sections = []
    for chunk in chunks:
        sections.append(
            "\n".join(
                [
                    f"Source document: {chunk.document_name}",
                    f"Document ID: {chunk.document_id}",
                    f"Chunk ID: {chunk.chunk_id}",
                    f"Chunk index: {chunk.chunk_index}",
                    f"Content: {chunk.content}",
                ]
            )
        )

    return "\n\n".join(sections)
