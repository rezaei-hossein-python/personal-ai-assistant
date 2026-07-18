from fastapi import FastAPI

from app.config import settings
from app.core.logging import logger, setup_logging
from app.routers.health import router as health_router
from app.routers.chat import router as chat_router

from app.database.database import engine, Base
from app.models import conversation, message


setup_logging()

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An AI-powered personal knowledge management system"
)


app.include_router(health_router)
app.include_router(chat_router)


@app.get("/")
def home():
    logger.info("Home endpoint accessed")

    return {
        "message": "Personal AI Assistant API is running",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION
    }