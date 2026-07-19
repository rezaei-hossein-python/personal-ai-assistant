from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.memory import MemoryCreate, MemoryResponse
from app.services.memory_service import (
    save_memory,
    get_memories,
    delete_memory,
)


router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryResponse)
def create_memory(
    request: MemoryCreate,
    db: Session = Depends(get_db),
):
    return save_memory(
        db=db,
        user_id=request.user_id,
        category=request.category,
        key=request.key,
        value=request.value,
    )


@router.get("/{user_id}", response_model=list[MemoryResponse])
def list_memories(
    user_id: int,
    db: Session = Depends(get_db),
):
    memories = get_memories(db, user_id)
    return memories


@router.delete("/{memory_id}")
def remove_memory(
    memory_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_memory(db, memory_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}
