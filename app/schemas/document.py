from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    content_type: str
    file_size: int
    processing_status: str
    error_message: str | None = None
    metadata: dict
    uploaded_at: datetime | None = None

    class Config:
        from_attributes = True


class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    metadata: dict

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class SearchResult(BaseModel):
    document_id: int
    document_name: str
    chunk_id: int
    chunk_index: int
    content: str
    metadata: dict
    start_character: int | None = None
    end_character: int | None = None
    distance: float | None = None
