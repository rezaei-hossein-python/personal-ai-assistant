from sqlalchemy.orm import Session

from app.models.memory import Memory


def save_memory(
    db: Session,
    user_id: int,
    category: str,
    key: str,
    value: str,
):
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
        .filter(
            Memory.user_id == user_id
        )
        .order_by(
            Memory.created_at.desc()
        )
        .all()
    )


def format_memories(
    memories: list,
):
    if not memories:
        return ""

    formatted = []

    for memory in memories:
        formatted.append(
            f"{memory.key}: {memory.value}"
        )

    return "\n".join(formatted)