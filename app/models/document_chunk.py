from sqlalchemy import Column, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import relationship

from app.core.embedding import EMBEDDING_DIMENSION
from app.database.database import Base
from app.database.vector import Vector


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSON, nullable=False, default=dict)
    embedding = Column(
        Vector(EMBEDDING_DIMENSION).with_variant(JSON, "sqlite"),
        nullable=True,
    )

    document = relationship("Document", back_populates="chunks")
