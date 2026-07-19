from sqlalchemy.orm import Session

from app.models.memory import Memory


def save_fact(
    db: Session,
    conversation_id: str,
    category: str,
    key: str,
    value: str,
):
    memory = Memory(
        conversation_id=conversation_id,
        category=category,
        key=key,
        value=value,
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory


def get_facts(
    db: Session,
    conversation_id: str,
):
    return (
        db.query(Memory)
        .filter(
            Memory.conversation_id == conversation_id
        )
        .all()
    )