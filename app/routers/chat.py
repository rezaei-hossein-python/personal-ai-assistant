import json

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
    save_memory,
)

from app.services.memory_extractor import (
    extract_memory,
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


    # Save user message
    save_message(
        request.conversation_id,
        "user",
        request.message,
    )


    # Extract possible long-term memory
    memory_result = extract_memory(
        request.message
    )

    try:

        memory_data = json.loads(
            memory_result
        )

        if memory_data.get("remember"):

            db = SessionLocal()

            save_memory(
                db=db,
                user_id=request.user_id,
                category=memory_data["category"],
                key=memory_data["key"],
                value=memory_data["value"],
            )

            db.close()

    except Exception as e:

        logger.error(
            f"Memory extraction failed: {e}"
        )


    # Load conversation history
    history = get_messages(
        request.conversation_id
    )


    # Load long-term memories
    db = SessionLocal()

    memories = get_memories(
        db,
        request.user_id,
    )

    db.close()


    # Generate AI response
    response = ask_ai(
        request.message,
        history,
        memories,
    )


    # Save assistant response
    save_message(
        request.conversation_id,
        "assistant",
        response,
    )


    return ChatResponse(
        response=response
    )