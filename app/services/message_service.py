from app.models.message import Message


def save_message(
    db,
    conversation_id: str,
    role: str,
    content: str,
    user_id: int | None = None,
    response_metadata: dict | None = None,
):
    message = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role=role,
        content=content,
        response_metadata=response_metadata,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_messages(
    db,
    conversation_id: str,
    user_id: int | None = None,
):
    query = db.query(Message).filter(
        Message.conversation_id == conversation_id
    )

    if user_id is not None:
        query = query.filter(Message.user_id == user_id)

    messages = query.order_by(Message.id).all()

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]
