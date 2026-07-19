from fastapi import APIRouter, HTTPException

from app.database.database import SessionLocal
from app.schemas.memory import MemoryResponse
from app.services.memory_service import (
    get_memories,
    delete_memory,
)


router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/{user_id}", response_model=list[MemoryResponse])
def list_memories(user_id: int):
    db = SessionLocal()
    memories = get_memories(db, user_id)
    db.close()
    return memories


@router.delete("/{memory_id}")
def remove_memory(memory_id: int):
    db = SessionLocal()
    deleted = delete_memory(db, memory_id)
    db.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}