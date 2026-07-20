from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_embedding_provider, get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    SearchRequest,
    SearchResult,
)
from app.services.document_service import (
    create_document_from_upload,
    delete_document,
    get_document,
    list_documents,
)
from app.services.embedding_service import EmbeddingProvider
from app.services.retrieval_service import (
    VectorSearchUnavailableError,
    retrieve_relevant_chunks,
)


router = APIRouter(prefix="/documents", tags=["documents"])


def document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        file_size=document.file_size,
        processing_status=document.processing_status,
        error_message=document.error_message,
        metadata=document.document_metadata or {},
        uploaded_at=document.uploaded_at,
    )


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_provider: EmbeddingProvider = Depends(get_current_embedding_provider),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    document = create_document_from_upload(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        embedding_provider=embedding_provider,
    )
    return document_response(document)


@router.get("", response_model=list[DocumentResponse])
def list_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        document_response(document)
        for document in list_documents(db, current_user.id)
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_my_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document(db, current_user.id, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return document_response(document)


@router.delete("/{document_id}")
def delete_my_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = delete_document(db, current_user.id, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": "Document deleted"}


@router.post("/search", response_model=list[SearchResult])
def search_my_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_provider: EmbeddingProvider = Depends(get_current_embedding_provider),
):
    try:
        chunks = retrieve_relevant_chunks(
            db=db,
            user_id=current_user.id,
            query=request.query,
            limit=request.limit,
            embedding_provider=embedding_provider,
        )
    except VectorSearchUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return [
        SearchResult(
            document_id=chunk.document_id,
            document_name=chunk.document_name,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            metadata=chunk.metadata,
            start_character=chunk.start_character,
            end_character=chunk.end_character,
            distance=chunk.distance,
        )
        for chunk in chunks
    ]
