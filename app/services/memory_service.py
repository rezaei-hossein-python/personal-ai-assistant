from sqlalchemy.orm import Session

from app.models.memory import Memory


def save_memory(
    db: Session,
    user_id: int,
    category: str,
    key: str,
    value: str,
):
    existing = (
        db.query(Memory)
        .filter(
            Memory.user_id == user_id,
            Memory.key == key,
        )
        .first()
    )

    if existing:
        existing.value = value
        existing.category = category
        db.commit()
        db.refresh(existing)
        return existing

    memory = Memory(
        user_id=user_id,
        category=category,
        key=key,
        value=value,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


def get_memories(
    db: Session,
    user_id: int,
):
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .all()
    )


def delete_memory(
    db: Session,
    memory_id: int,
    user_id: int,
):
    memory = (
        db.query(Memory)
        .filter(
            Memory.id == memory_id,
            Memory.user_id == user_id,
        )
        .first()
    )

    if not memory:
        return False

    db.delete(memory)
    db.commit()

    return True
