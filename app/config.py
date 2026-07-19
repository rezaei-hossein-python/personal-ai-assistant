from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Personal AI Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "change-me-in-development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = (
        "postgresql+psycopg2://username:password@localhost:5432/personal_ai"
    )

    class Config:
        env_file = ".env"


settings = Settings()
