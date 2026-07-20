from sqlalchemy.orm import Session

from app.agents.types import MemoryContext
from app.services.memory_service import retrieve_memories


class MemoryAgent:
    name = "MemoryAgent"

    def get_context(
        self,
        db: Session,
        user_id: int,
        query: str,
        enabled: bool,
    ) -> MemoryContext:
        if not enabled:
            return MemoryContext(
                memories=[],
                metadata={"enabled": False, "memory_count": 0},
            )

        memories = retrieve_memories(db, user_id, query)
        return MemoryContext(
            memories=memories,
            metadata={
                "enabled": True,
                "memory_count": len(memories),
            },
        )
