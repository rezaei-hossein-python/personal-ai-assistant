from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.core.logging import setup_logging
from app.database.database import check_database_connection
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.memories import router as memories_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    check_database_connection()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An AI-powered personal knowledge management system",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "message": "Personal AI Assistant API is running"
    }


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(memories_router)
