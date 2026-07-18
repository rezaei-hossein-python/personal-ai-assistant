from fastapi import APIRouter

from app.core.logging import logger
from app.services.ai_service import ask_ai


router = APIRouter()


@router.post("/chat")
def chat(message: str):
    logger.info("Chat request received")

    response = ask_ai(message)

    return {
        "response": response
    }