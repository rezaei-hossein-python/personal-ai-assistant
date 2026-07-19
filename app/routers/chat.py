import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database.database import get_db

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.ai_service import ask_ai
from app.services.conversation_service import get_or_create_conversation

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


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):

    logger.info(
        f"Chat request received for conversation {request.conversation_id}"
    )

    get_or_create_conversation(
        db,
        request.conversation_id,
        request.user_id,
    )


    # Save user message
    save_message(
        db,
        request.conversation_id,
        "user",
        request.message,
        request.user_id,
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

            save_memory(
                db=db,
                user_id=request.user_id,
                category=memory_data["category"],
                key=memory_data["key"],
                value=memory_data["value"],
            )

    except Exception as e:

        logger.error(
            f"Memory extraction failed: {e}"
        )


    # Load conversation history
    history = get_messages(
        db,
        request.conversation_id
    )


    # Load long-term memories
    memories = get_memories(
        db,
        request.user_id,
    )


    # Generate AI response
    response = ask_ai(
        request.message,
        history,
        memories,
    )


    # Save assistant response
    save_message(
        db,
        request.conversation_id,
        "assistant",
        response,
        request.user_id,
    )


    return ChatResponse(
        response=response
    )
