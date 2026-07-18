from fastapi import APIRouter

from app.core.logging import logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import ask_ai
from app.services.memory_service import save_message, get_conversation


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    logger.info(
        f"Chat request received for conversation {request.conversation_id}"
    )

    save_message(
        request.conversation_id,
        "user",
        request.message
    )

    history = get_conversation(
        request.conversation_id
    )

    response = ask_ai(
        request.message,
        history
    )

    save_message(
        request.conversation_id,
        "assistant",
        response
    )

    return ChatResponse(
        response=response
    )