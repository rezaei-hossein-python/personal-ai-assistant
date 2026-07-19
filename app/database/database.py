from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# Import models so SQLAlchemy and Alembic can discover them
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.memory import Memory