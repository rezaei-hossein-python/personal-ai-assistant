from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def create_database_engine(database_url: str):
    if not database_url:
        database_url = "sqlite:///./assistant.db"

    if database_url.startswith("sqlite"):
        return create_engine(database_url)

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception:
        return create_engine("sqlite:///./assistant.db")


engine = create_database_engine(settings.DATABASE_URL)

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