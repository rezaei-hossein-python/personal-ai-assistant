from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import (
    get_chat_orchestrator,
    get_current_embedding_provider,
    get_current_model_provider,
    get_current_user,
)
from app.models.user import User
from app.orchestrators.chat_orchestrator import ChatOrchestrator
from app.providers.model_provider import ModelProvider
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingProvider


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_provider: ModelProvider = Depends(get_current_model_provider),
    embedding_provider: EmbeddingProvider = Depends(get_current_embedding_provider),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
):
    response = orchestrator.handle_chat(
        db=db,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        message=request.message,
        model_provider=model_provider,
        embedding_provider=embedding_provider,
    )

    return ChatResponse(response=response)
