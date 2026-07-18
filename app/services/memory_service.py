from app.core.logging import logger

from app.database.database import SessionLocal
from app.models.message import Message


def save_message(
    conversation_id: str,
    role: str,
    content: str
):

    logger.info(
        f"Saving message for conversation {conversation_id}"
    )

    db = SessionLocal()

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()
    db.close()


def get_conversation(conversation_id: str):

    logger.info(
        f"Retrieving memory for conversation {conversation_id}"
    )

    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(
            Message.id
        )
        .all()
    )

    db.close()

    return [
        {
            "role": message.role,
            "content": message.content
        }
        for message in messages
    ]