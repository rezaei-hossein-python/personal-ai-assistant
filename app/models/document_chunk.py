from sqlalchemy import Column, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


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

    document = relationship("Document", back_populates="chunks")
