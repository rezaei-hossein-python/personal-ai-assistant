from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "conversation_id"],
            ["conversations.user_id", "conversations.conversation_id"],
            name="fk_messages_conversation_owner",
            ondelete="CASCADE",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        String,
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    role = Column(
        String,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship("User", back_populates="messages", overlaps="conversation,messages")
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        primaryjoin=(
            "and_(Conversation.user_id == foreign(Message.user_id), "
            "Conversation.conversation_id == foreign(Message.conversation_id))"
        ),
        foreign_keys="[Message.user_id, Message.conversation_id]",
        overlaps="messages,user",
    )
