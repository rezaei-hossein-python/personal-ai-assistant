from fastapi import FastAPI

from app.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An AI-powered personal knowledge management system"
)


@app.get("/")
def home():
    return {
        "message": "Personal AI Assistant API is running",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION
    }