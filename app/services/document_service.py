import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider
from app.services.text_extraction_service import TextExtractionError, extract_text


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name:
        return "document"
    return name[:255]


def create_document_from_upload(
    db: Session,
    user_id: int,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    embedding_provider: EmbeddingProvider | None = None,
) -> Document:
    safe_filename = sanitize_filename(filename)
    logger.info(
        "Starting document ingestion user_id=%s filename=%s size=%s",
        user_id,
        safe_filename,
        len(file_bytes),
    )
    document = Document(
        user_id=user_id,
        original_filename=safe_filename,
        content_type=content_type,
        file_size=len(file_bytes),
        processing_status="processing",
        document_metadata={},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        text, metadata = extract_text(
            file_bytes=file_bytes,
            filename=safe_filename,
            content_type=content_type,
        )
        chunks = chunk_text(text)

        document.document_metadata = metadata | {
            "character_count": len(text),
            "chunk_count": len(chunks),
        }

        if not chunks:
            document.processing_status = "failed"
            document.error_message = "No extractable text found"
        else:
            provider = embedding_provider or get_embedding_provider()
            for chunk in chunks:
                embedding = provider.embed_text(chunk.content)
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        chunk_metadata=chunk.metadata,
                        embedding=embedding,
                    )
                )
            document.processing_status = "completed"
            document.error_message = None

        db.commit()
        db.refresh(document)
        logger.info(
            "Document ingestion completed user_id=%s document_id=%s status=%s chunks=%s",
            user_id,
            document.id,
            document.processing_status,
            document.document_metadata.get("chunk_count", 0),
        )
        return document

    except TextExtractionError as exc:
        document.processing_status = "failed"
        document.error_message = str(exc)
        document.document_metadata = {}
        db.commit()
        db.refresh(document)
        logger.warning(
            "Document ingestion failed user_id=%s document_id=%s reason=%s",
            user_id,
            document.id,
            type(exc).__name__,
        )
        return document
    except Exception as exc:
        document.processing_status = "failed"
        document.error_message = "Failed to generate embeddings"
        document.document_metadata = {}
        db.commit()
        db.refresh(document)
        logger.exception(
            "Document embedding failed user_id=%s document_id=%s",
            user_id,
            document.id,
        )
        return document


def list_documents(
    db: Session,
    user_id: int,
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.uploaded_at.desc(), Document.id.desc())
        .all()
    )


def get_document(
    db: Session,
    user_id: int,
    document_id: int,
) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        .first()
    )


def delete_document(
    db: Session,
    user_id: int,
    document_id: int,
) -> bool:
    document = get_document(db, user_id, document_id)
    if document is None:
        return False

    db.delete(document)
    db.commit()
    return True
