from app.database.database import SessionLocal
from app.models.message import Message


def save_message(
    conversation_id: str,
    role: str,
    content: str,
):
    db = SessionLocal()

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    db.close()

    return message


def get_messages(
    conversation_id: str,
):
    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(Message.id)
        .all()
    )

    db.close()

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]