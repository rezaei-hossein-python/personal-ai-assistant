import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

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
from app.services.retrieval_service import (
    VectorSearchUnavailableError,
    retrieve_relevant_chunks,
)


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    logger.info(
        f"Chat request received for conversation {request.conversation_id}"
    )

    get_or_create_conversation(
        db,
        request.conversation_id,
        current_user.id,
    )


    # Save user message
    save_message(
        db,
        request.conversation_id,
        "user",
        request.message,
        current_user.id,
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
                user_id=current_user.id,
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
        request.conversation_id,
        current_user.id,
    )


    # Load long-term memories
    memories = get_memories(
        db,
        current_user.id,
    )

    try:
        document_chunks = retrieve_relevant_chunks(
            db=db,
            user_id=current_user.id,
            query=request.message,
        )
    except VectorSearchUnavailableError:
        document_chunks = []


    # Generate AI response
    response = ask_ai(
        request.message,
        history,
        memories,
        document_chunks,
    )


    # Save assistant response
    save_message(
        db,
        request.conversation_id,
        "assistant",
        response,
        current_user.id,
    )


    return ChatResponse(
        response=response
    )
