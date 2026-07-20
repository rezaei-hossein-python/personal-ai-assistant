from sqlalchemy import func

from app.core.logging import logger
from app.models.conversation import Conversation
from app.models.message import Message


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


def get_conversation(
    db,
    conversation_id: str,
    user_id: int | None = None,
):
    logger.info(
        f"Getting conversation {conversation_id}"
    )

    query = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    )

    if user_id is not None:
        query = query.filter(Conversation.user_id == user_id)

    conversation = query.first()

    return conversation


def get_or_create_conversation(
    db,
    conversation_id: str,
    user_id: int | None = None,
):
    conversation = get_conversation(
        db,
        conversation_id,
        user_id,
    )

    if conversation:
        return conversation

    return create_conversation(
        db,
        conversation_id,
        user_id,
    )


def list_conversations(db, user_id: int):
    latest_message_at = (
        db.query(func.max(Message.created_at))
        .filter(
            Message.user_id == Conversation.user_id,
            Message.conversation_id == Conversation.conversation_id,
        )
        .correlate(Conversation)
        .scalar_subquery()
    )

    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(
            latest_message_at.desc().nullslast(),
            Conversation.created_at.desc(),
        )
        .all()
    )


def delete_conversation(db, conversation_id: str, user_id: int) -> bool:
    conversation = get_conversation(db, conversation_id, user_id)
    if conversation is None:
        return False

    db.delete(conversation)
    db.commit()
    return True
