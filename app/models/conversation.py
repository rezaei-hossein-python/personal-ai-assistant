from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", name="uq_conversations_user_conversation"),
        Index(
            "ix_conversations_user_conversation_id",
            "user_id",
            "conversation_id",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(String, nullable=False, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title = Column(String, nullable=False, default="New Conversation")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        primaryjoin=(
            "and_(Conversation.user_id == foreign(Message.user_id), "
            "Conversation.conversation_id == foreign(Message.conversation_id))"
        ),
        foreign_keys="[Message.user_id, Message.conversation_id]",
        cascade="all, delete-orphan",
        overlaps="messages,user",
    )
