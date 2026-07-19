from sqlalchemy.orm import Session

from app.models.memory import Memory


def save_fact(
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


def get_facts(
    db: Session,
    user_id: int,
):
    return (
        db.query(Memory)
        .filter(
            Memory.user_id == user_id
        )
        .all()
    )
