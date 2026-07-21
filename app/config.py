import json
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Personal AI Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    DESKTOP_MODE: bool = False
    DESKTOP_DATA_DIR: str = ""
    DESKTOP_LOG_DIR: str = ""
    DESKTOP_FRONTEND_DIR: str = ""
    DATABASE_BACKEND: str = "postgres"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_MODEL: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-latest"
    MODEL_PROVIDER_DEFAULT: str = "openai"
    MODEL_COLLABORATION_ENABLED: bool = False
    JWT_SECRET_KEY: str = ""
    SECRET_KEY: str = "change-me-in-development"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = (
        "postgresql+psycopg2://username:password@localhost:5432/personal_ai"
    )
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    TRUSTED_HOSTS: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    LOG_LEVEL: str = "INFO"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    FRONTEND_PUBLIC_URL: str = "http://localhost:5173"
    API_PUBLIC_URL: str = "http://localhost:8000"
    API_DOCS_ENABLED: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_CONNECT_TIMEOUT_SECONDS: int = 10
    DB_STARTUP_RETRY_ATTEMPTS: int = 5
    DB_STARTUP_RETRY_DELAY_SECONDS: int = 2
    DESKTOP_SCHEMA_VERSION: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_string_list(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    raise ValueError("Expected a JSON list")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        raise ValueError("Expected a comma-separated string or JSON list")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("DATABASE_BACKEND")
    @classmethod
    def validate_database_backend(cls, value: str) -> str:
        normalized = value.lower()
        allowed = {"postgres", "sqlite"}
        if normalized not in allowed:
            raise ValueError(
                f"DATABASE_BACKEND must be one of {', '.join(sorted(allowed))}"
            )
        return normalized

    @model_validator(mode="after")
    def normalize_aliases(self):
        if self.JWT_SECRET_KEY:
            self.SECRET_KEY = self.JWT_SECRET_KEY
        else:
            self.JWT_SECRET_KEY = self.SECRET_KEY

        if self.EMBEDDING_MODEL:
            self.OPENAI_EMBEDDING_MODEL = self.EMBEDDING_MODEL
        else:
            self.EMBEDDING_MODEL = self.OPENAI_EMBEDDING_MODEL

        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    def validate_for_startup(self) -> None:
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
        if self.MAX_UPLOAD_BYTES <= 0:
            raise RuntimeError("MAX_UPLOAD_BYTES must be greater than zero")
        if self.DB_STARTUP_RETRY_ATTEMPTS < 1:
            raise RuntimeError("DB_STARTUP_RETRY_ATTEMPTS must be at least 1")

        if self.DESKTOP_MODE:
            if self.API_HOST != "127.0.0.1":
                raise RuntimeError("Desktop mode must bind API_HOST to 127.0.0.1")
            if self.DATABASE_BACKEND != "sqlite":
                raise RuntimeError("Desktop mode requires DATABASE_BACKEND=sqlite")
            if "*" in self.ALLOWED_ORIGINS:
                raise RuntimeError("Desktop mode cannot use wildcard CORS")
            return

        if not self.is_production:
            return

        missing = []
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if missing:
            raise RuntimeError(
                "Missing required production settings: " + ", ".join(missing)
            )
        if self.JWT_SECRET_KEY == "change-me-in-development":
            raise RuntimeError("JWT_SECRET_KEY must be changed for production")
        if len(self.JWT_SECRET_KEY) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")
        if "*" in self.ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS cannot include '*' in production")
        if self.API_DOCS_ENABLED:
            raise RuntimeError("API_DOCS_ENABLED must be false in production")


settings = Settings()
