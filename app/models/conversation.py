from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    conversation_id = Column(
        String,
        nullable=False,
        unique=True,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=True,
        index=True
    )

    title = Column(
        String,
        nullable=False,
        default="New Conversation"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        primaryjoin="Conversation.conversation_id == Message.conversation_id",
    )
