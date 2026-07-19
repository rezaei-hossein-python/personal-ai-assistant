from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Personal AI Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-latest"
    MODEL_PROVIDER_DEFAULT: str = "openai"
    MODEL_COLLABORATION_ENABLED: bool = False
    SECRET_KEY: str = "change-me-in-development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = (
        "postgresql+psycopg2://username:password@localhost:5432/personal_ai"
    )

    class Config:
        env_file = ".env"


settings = Settings()
