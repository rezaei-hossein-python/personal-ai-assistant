from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider


@dataclass
class EmbeddingBackfillResult:
    scanned_count: int
    updated_count: int
    skipped_count: int
    failed_count: int


def backfill_missing_chunk_embeddings(
    db: Session,
    embedding_provider: EmbeddingProvider | None = None,
    batch_size: int = 100,
) -> EmbeddingBackfillResult:
    provider = embedding_provider or get_embedding_provider()
    total_count = db.query(DocumentChunk).count()
    query = db.query(DocumentChunk)
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        query = query.filter(text("embedding IS NULL OR embedding = 'null'"))
    else:
        query = query.filter(DocumentChunk.embedding.is_(None))

    chunks = (
        query
        .order_by(DocumentChunk.id)
        .limit(batch_size)
        .all()
    )

    scanned_count = len(chunks)
    updated_count = 0
    failed_count = 0

    for chunk in chunks:
        try:
            chunk.embedding = provider.embed_text(chunk.content)
            updated_count += 1
        except Exception:
            failed_count += 1

    db.commit()

    return EmbeddingBackfillResult(
        scanned_count=scanned_count,
        updated_count=updated_count,
        skipped_count=max(0, total_count - scanned_count),
        failed_count=failed_count,
    )
