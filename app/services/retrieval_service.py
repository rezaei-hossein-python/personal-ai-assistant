from dataclasses import dataclass
import math

from sqlalchemy import text
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
    if db.bind is None:
        return False

    if db.bind.dialect.name == "sqlite":
        return True

    if db.bind.dialect.name != "postgresql":
        return False

    row = db.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).first()
    return row is not None


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
    query_embedding = provider.embed_text(query)

    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return _retrieve_with_python_cosine(
            db=db,
            user_id=user_id,
            query_embedding=query_embedding,
            limit=limit,
        )

    vector_literal = _format_vector(query_embedding)
    rows = db.execute(
        text(
            """
            SELECT
                dc.id AS chunk_id,
                dc.document_id AS document_id,
                dc.chunk_index AS chunk_index,
                dc.content AS content,
                dc.metadata AS metadata,
                d.original_filename AS document_name,
                dc.embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.user_id = :user_id
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        ),
        {
            "query_embedding": vector_literal,
            "user_id": user_id,
            "limit": limit,
        },
    ).mappings().all()

    return [
        RetrievedChunk(
            document_id=row["document_id"],
            document_name=row["document_name"],
            chunk_id=row["chunk_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            metadata=row["metadata"] or {},
        )
        for row in rows
    ]


def _retrieve_with_python_cosine(
    db: Session,
    user_id: int,
    query_embedding: list[float],
    limit: int,
) -> list[RetrievedChunk]:
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.user_id == user_id,
            DocumentChunk.embedding.isnot(None),
        )
        .all()
    )

    ranked = sorted(
        [
            (
                _cosine_distance(query_embedding, chunk.embedding),
                chunk,
                document,
            )
            for chunk, document in rows
        ],
        key=lambda item: item[0],
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
        for _, chunk, document in ranked[:limit]
    ]


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def _cosine_distance(
    left: list[float],
    right: list[float],
) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return 1.0

    return 1 - (dot_product / (left_norm * right_norm))


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
