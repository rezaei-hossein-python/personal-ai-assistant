from app.core.logging import logger
from app.models.conversation import Conversation


def create_conversation(db, conversation_id: str, user_id: int | None = None):
    logger.info(
        f"Creating conversation {conversation_id}"
    )

    conversation = Conversation(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation(db, conversation_id: str):
    logger.info(
        f"Getting conversation {conversation_id}"
    )

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.conversation_id == conversation_id
        )
        .first()
    )

    return conversation


def get_or_create_conversation(
    db,
    conversation_id: str,
    user_id: int | None = None,
):
    conversation = get_conversation(
        db,
        conversation_id,
    )

    if conversation:
        return conversation

    return create_conversation(
        db,
        conversation_id,
        user_id,
    )
