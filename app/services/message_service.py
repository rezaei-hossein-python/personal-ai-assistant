from app.models.message import Message


def save_message(
    db,
    conversation_id: str,
    role: str,
    content: str,
    user_id: int | None = None,
):
    message = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_messages(
    db,
    conversation_id: str,
):
    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(Message.id)
        .all()
    )

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]
