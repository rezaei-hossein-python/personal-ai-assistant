from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.database.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        String,
        index=True
    )

    role = Column(
        String
    )

    content = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )