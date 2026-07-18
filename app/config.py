from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Personal AI Assistant"
    APP_VERSION: str = "0.1.0"

    OPENAI_API_KEY: str
    DATABASE_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()