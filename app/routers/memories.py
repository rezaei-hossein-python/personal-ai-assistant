from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
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
    current_user: User = Depends(get_current_user),
):
    return save_memory(
        db=db,
        user_id=current_user.id,
        category=request.category,
        key=request.key,
        value=request.value,
    )


@router.get("", response_model=list[MemoryResponse])
def list_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memories = get_memories(db, current_user.id)
    return memories


@router.delete("/{memory_id}")
def remove_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = delete_memory(db, memory_id, current_user.id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}
