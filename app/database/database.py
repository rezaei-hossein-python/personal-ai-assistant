import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings
from app.core.logging import logger


def validate_database_url(database_url: str, app_env: str | None = None):
    app_env = app_env or settings.APP_ENV
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
    url = make_url(database_url)
    connect_args = {}
    engine_options = {
        "pool_pre_ping": True,
    }
    if url.drivername.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        connect_args["connect_timeout"] = settings.DB_CONNECT_TIMEOUT_SECONDS
        engine_options.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
            }
        )

    try:
        return create_engine(
            database_url,
            connect_args=connect_args,
            **engine_options,
        )
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


def wait_for_database() -> None:
    attempts = settings.DB_STARTUP_RETRY_ATTEMPTS
    delay = settings.DB_STARTUP_RETRY_DELAY_SECONDS

    for attempt in range(1, attempts + 1):
        try:
            check_database_connection()
            logger.info("Database connection verified")
            return
        except RuntimeError:
            if attempt >= attempts:
                logger.exception("Database unavailable after %s attempts", attempts)
                raise
            logger.warning(
                "Database unavailable; retrying attempt=%s max_attempts=%s",
                attempt,
                attempts,
            )
            time.sleep(delay)
