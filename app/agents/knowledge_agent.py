from sqlalchemy.orm import Session

from app.agents.types import KnowledgeContext
from app.services.embedding_service import EmbeddingProvider
from app.services.retrieval_service import (
    VectorSearchUnavailableError,
    retrieve_relevant_chunks,
)


class KnowledgeAgent:
    name = "KnowledgeAgent"

    def get_context(
        self,
        db: Session,
        user_id: int,
        query: str,
        enabled: bool,
        embedding_provider: EmbeddingProvider,
    ) -> KnowledgeContext:
        if not enabled:
            return KnowledgeContext(
                chunks=[],
                metadata={"enabled": False, "retrieval_count": 0},
            )

        try:
            chunks = retrieve_relevant_chunks(
                db=db,
                user_id=user_id,
                query=query,
                embedding_provider=embedding_provider,
            )
            return KnowledgeContext(
                chunks=chunks,
                metadata={
                    "enabled": True,
                    "retrieval_count": len(chunks),
                },
            )
        except VectorSearchUnavailableError as exc:
            return KnowledgeContext(
                chunks=[],
                metadata={
                    "enabled": True,
                    "retrieval_count": 0,
                    "warning": str(exc),
                },
            )
