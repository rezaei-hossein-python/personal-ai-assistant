from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


def validate_database_url(database_url: str, app_env: str = settings.APP_ENV):
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    try:
        url = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("DATABASE_URL is invalid") from exc

    drivername = url.drivername.lower()
    is_postgres = drivername.startswith("postgresql")
    is_test_sqlite = app_env == "test" and drivername.startswith("sqlite")

    if not is_postgres and not is_test_sqlite:
        raise RuntimeError(
            "DATABASE_URL must use PostgreSQL. SQLite is only allowed when "
            "APP_ENV=test."
        )


def create_database_engine(database_url: str):
    validate_database_url(database_url)
    try:
        return create_engine(database_url, pool_pre_ping=True)
    except Exception as exc:
        raise RuntimeError(
            "Failed to create database engine from DATABASE_URL"
        ) from exc


engine = create_database_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database connection failed. Check DATABASE_URL and ensure "
            "PostgreSQL is running and migrated."
        ) from exc


# Import models so SQLAlchemy and Alembic can discover them
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.models.memory import Memory
from app.models.user import User
