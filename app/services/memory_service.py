import re

from sqlalchemy.orm import Session

from app.models.memory import Memory


MEMORY_RETRIEVAL_LIMIT = 8


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


def retrieve_memories(
    db: Session,
    user_id: int,
    query: str,
    limit: int = MEMORY_RETRIEVAL_LIMIT,
):
    memories = get_memories(db, user_id)
    query_tokens = _tokenize(query)

    if not query_tokens:
        return memories[:limit]

    ranked = []
    for memory in memories:
        score = _memory_score(memory, query_tokens)
        if score > 0:
            ranked.append((score, memory))

    ranked.sort(
        key=lambda item: (
            item[0],
            item[1].updated_at or item[1].created_at,
            item[1].id,
        ),
        reverse=True,
    )

    return [memory for _, memory in ranked[:limit]]


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


def _memory_score(memory: Memory, query_tokens: set[str]) -> int:
    key_tokens = _tokenize(memory.key)
    value_tokens = _tokenize(memory.value)
    category_tokens = _tokenize(memory.category)

    return (
        len(query_tokens & key_tokens) * 3
        + len(query_tokens & value_tokens) * 2
        + len(query_tokens & category_tokens)
    )


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\b[a-z0-9]+\b", text.lower().replace("_", " "))
        if len(token) > 1
    }
