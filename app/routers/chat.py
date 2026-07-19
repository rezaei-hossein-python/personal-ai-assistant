from fastapi import APIRouter

from app.core.logging import logger

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.ai_service import ask_ai

from app.services.message_service import (
    save_message,
    get_messages,
)

from app.services.memory_service import (
    get_memories,
)

from app.database.database import SessionLocal


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(request: ChatRequest):

    logger.info(
        f"Chat request received for conversation {request.conversation_id}"
    )


    save_message(
        request.conversation_id,
        "user",
        request.message,
    )


    history = get_messages(
        request.conversation_id
    )


    db = SessionLocal()

    memories = get_memories(
        db,
        request.user_id,
    )

    db.close()


    response = ask_ai(
        request.message,
        history,
        memories,
    )


    save_message(
        request.conversation_id,
        "assistant",
        response,
    )


    return ChatResponse(
        response=response
    )