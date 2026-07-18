from fastapi import APIRouter

from app.core.logging import logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import ask_ai


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    logger.info(
        f"Chat request received for conversation {request.conversation_id}"
    )

    response = ask_ai(request.message)

    return ChatResponse(
        response=response
    )