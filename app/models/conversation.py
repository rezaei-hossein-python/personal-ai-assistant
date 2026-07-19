from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String

from app.database.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "ix_conversations_user_conversation_id",
            "user_id",
            "conversation_id",
            unique=True,
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    conversation_id = Column(
        String,
        nullable=False,
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
