from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

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
        unique=True,
        index=True
    )

    title = Column(
        String,
        default="New Conversation"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )