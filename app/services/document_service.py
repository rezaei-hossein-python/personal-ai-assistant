from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider
from app.services.text_extraction_service import TextExtractionError, extract_text


def create_document_from_upload(
    db: Session,
    user_id: int,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    embedding_provider: EmbeddingProvider | None = None,
) -> Document:
    document = Document(
        user_id=user_id,
        original_filename=filename,
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
            filename=filename,
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
        return document

    except TextExtractionError as exc:
        document.processing_status = "failed"
        document.error_message = str(exc)
        document.document_metadata = {}
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:
        document.processing_status = "failed"
        document.error_message = f"Failed to generate embeddings: {exc}"
        document.document_metadata = {}
        db.commit()
        db.refresh(document)
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
