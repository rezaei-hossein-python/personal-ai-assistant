from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.orchestrators.chat_orchestrator import ChatOrchestrator
from app.providers.model_provider import ModelProvider
from app.providers.model_router import ModelRouter
from app.providers.openai_provider import OpenAIModelProvider
from app.services.auth_service import decode_access_token
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider
from app.services.user_service import get_user_by_id


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def get_current_embedding_provider() -> EmbeddingProvider:
    return get_embedding_provider()


def get_current_model_provider() -> ModelProvider:
    return OpenAIModelProvider()


def get_model_router() -> ModelRouter:
    return ModelRouter()


def get_chat_orchestrator() -> ChatOrchestrator:
    return ChatOrchestrator()
