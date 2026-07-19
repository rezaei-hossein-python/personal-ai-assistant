from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Personal AI Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = (
        "postgresql+psycopg2://username:password@localhost:5432/personal_ai"
    )

    class Config:
        env_file = ".env"


settings = Settings()
