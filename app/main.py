from fastapi import FastAPI

from app.routers.chat import router as chat_router
from app.routers.memories import router as memories_router


app = FastAPI(
    title="Personal AI Assistant",
    version="0.1.0",
    description="An AI-powered personal knowledge management system",
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def home():
    return {
        "message": "Personal AI Assistant API is running"
    }


app.include_router(chat_router)
app.include_router(memories_router)