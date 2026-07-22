import time

from sqlalchemy import create_engine, event, text
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
    is_desktop_sqlite = settings.DESKTOP_MODE and drivername.startswith("sqlite")

    if not is_postgres and not is_test_sqlite and not is_desktop_sqlite:
        raise RuntimeError(
            "DATABASE_URL must use PostgreSQL. SQLite is only allowed when "
            "APP_ENV=test or DESKTOP_MODE=true."
        )

    if settings.DATABASE_BACKEND == "sqlite" and not drivername.startswith("sqlite"):
        raise RuntimeError("DATABASE_BACKEND=sqlite requires a SQLite DATABASE_URL")
    if settings.DATABASE_BACKEND == "postgres" and not is_postgres and not is_test_sqlite:
        raise RuntimeError("DATABASE_BACKEND=postgres requires a PostgreSQL DATABASE_URL")


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
        created_engine = create_engine(
            database_url,
            connect_args=connect_args,
            **engine_options,
        )
        if url.drivername.startswith("sqlite"):
            _configure_sqlite_engine(created_engine)
        return created_engine
    except Exception as exc:
        raise RuntimeError(
            "Failed to create database engine from DATABASE_URL"
        ) from exc


def _configure_sqlite_engine(sqlite_engine):
    @event.listens_for(sqlite_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_database_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def initialize_desktop_database() -> None:
    if not settings.DESKTOP_MODE:
        return
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Desktop database initialization requires SQLite")

    import app.models  # noqa: F401

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS desktop_schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        row = connection.execute(
            text("SELECT version FROM desktop_schema_version WHERE id = 1")
        ).first()
        if row is None:
            connection.execute(
                text(
                    "INSERT INTO desktop_schema_version (id, version) "
                    "VALUES (1, :version)"
                ),
                {"version": settings.DESKTOP_SCHEMA_VERSION},
            )
        elif int(row.version) > settings.DESKTOP_SCHEMA_VERSION:
            raise RuntimeError(
                "Desktop database schema is newer than this application version"
            )

    Base.metadata.create_all(bind=engine)
    _reconcile_desktop_schema()
    logger.info(
        "Desktop database initialized schema_version=%s",
        settings.DESKTOP_SCHEMA_VERSION,
    )


def _reconcile_desktop_schema() -> None:
    if not settings.DESKTOP_MODE:
        return
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Desktop schema reconciliation requires SQLite")

    with engine.begin() as connection:
        message_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(messages)")).all()
        }
        if "response_metadata" not in message_columns:
            connection.execute(
                text("ALTER TABLE messages ADD COLUMN response_metadata JSON")
            )
            logger.info("Desktop schema added messages.response_metadata")

        connection.execute(
            text(
                """
                UPDATE desktop_schema_version
                SET version = :version,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1 AND version < :version
                """
            ),
            {"version": settings.DESKTOP_SCHEMA_VERSION},
        )


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
