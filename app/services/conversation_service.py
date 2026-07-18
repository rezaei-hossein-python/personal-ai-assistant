from app.core.logging import logger

from app.database.database import SessionLocal
from app.models.conversation import Conversation


def create_conversation(conversation_id: str):
    logger.info(
        f"Creating conversation {conversation_id}"
    )

    db = SessionLocal()

    conversation = Conversation(
        conversation_id=conversation_id
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    db.close()

    return conversation


def get_conversation(conversation_id: str):
    logger.info(
        f"Getting conversation {conversation_id}"
    )

    db = SessionLocal()

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.conversation_id == conversation_id
        )
        .first()
    )

    db.close()

    return conversation


def get_or_create_conversation(conversation_id: str):
    conversation = get_conversation(
        conversation_id
    )

    if conversation:
        return conversation

    return create_conversation(
        conversation_id
    )