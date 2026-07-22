import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database.database import get_db
from app.dependencies import (
    get_chat_orchestrator,
    get_current_embedding_provider,
    get_current_model_provider,
    get_current_user,
    get_model_router,
)
from app.models.user import User
from app.orchestrators.chat_orchestrator import ChatOrchestrator
from app.providers.model_provider import ModelProvider
from app.providers.model_router import ModelRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding_service import EmbeddingProvider


router = APIRouter()


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_provider: ModelProvider = Depends(get_current_model_provider),
    model_router: ModelRouter = Depends(get_model_router),
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
        model_router=model_router,
        knowledge_retrieval=request.knowledge_retrieval,
        memory_retrieval=request.memory_retrieval,
    )

    return ChatResponse(
        response=response.response,
        metadata=response.metadata,
    )


@router.post("/chat/stream")
def stream_chat(
    http_request: Request,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_provider: ModelProvider = Depends(get_current_model_provider),
    model_router: ModelRouter = Depends(get_model_router),
    embedding_provider: EmbeddingProvider = Depends(get_current_embedding_provider),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
):
    async def event_stream():
        disconnected = False
        emitted_first_delta = False
        checked_after_first_delta = False
        request_id = http_request.headers.get("x-request-id", "-")

        async def check_disconnect(stage: str) -> bool:
            nonlocal disconnected
            is_disconnected = await http_request.is_disconnected()
            logger.info(
                "stream lifecycle checkpoint request_id=%s conversation_id=%s "
                "stage=%s is_disconnected=%s",
                request_id,
                request.conversation_id,
                stage,
                is_disconnected,
            )
            if is_disconnected != disconnected:
                disconnected = is_disconnected
                if is_disconnected:
                    logger.info(
                        "stream client disconnected request_id=%s conversation_id=%s "
                        "stage=%s",
                        request_id,
                        request.conversation_id,
                        stage,
                    )
            return is_disconnected

        logger.info(
            "stream opened request_id=%s conversation_id=%s",
            request_id,
            request.conversation_id,
        )
        try:
            await check_disconnect("after_stream_open")
            for item in orchestrator.stream_chat(
                db=db,
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                message=request.message,
                model_provider=model_provider,
                embedding_provider=embedding_provider,
                model_router=model_router,
                knowledge_retrieval=request.knowledge_retrieval,
                memory_retrieval=request.memory_retrieval,
            ):
                if item.event == "__checkpoint":
                    stage = item.data["stage"]
                    if await check_disconnect(stage):
                        raise asyncio.CancelledError()
                    continue

                if item.event == "delta" and not emitted_first_delta:
                    if await check_disconnect("before_first_delta"):
                        raise asyncio.CancelledError()

                if item.event == "complete":
                    if await check_disconnect("before_complete"):
                        raise asyncio.CancelledError()

                if await check_disconnect(f"before_emit_{item.event}"):
                    raise asyncio.CancelledError()
                if item.event == "start":
                    logger.info(
                        "start event emitted request_id=%s conversation_id=%s",
                        request_id,
                        request.conversation_id,
                    )
                elif item.event == "delta" and not emitted_first_delta:
                    logger.info(
                        "first delta emitted request_id=%s conversation_id=%s",
                        request_id,
                        request.conversation_id,
                    )
                    emitted_first_delta = True
                elif item.event == "complete":
                    logger.info(
                        "complete event emitted request_id=%s conversation_id=%s",
                        request_id,
                        request.conversation_id,
                    )
                yield _format_sse(item.event, item.data)
                if item.event == "delta" and not checked_after_first_delta:
                    checked_after_first_delta = True
                    if await check_disconnect("after_first_delta"):
                        raise asyncio.CancelledError()
                else:
                    await check_disconnect(f"after_emit_{item.event}")
        except asyncio.CancelledError:
            logger.info(
                "stream CancelledError request_id=%s conversation_id=%s",
                request_id,
                request.conversation_id,
            )
            raise
        except GeneratorExit:
            logger.info(
                "stream GeneratorExit request_id=%s conversation_id=%s",
                request_id,
                request.conversation_id,
            )
            raise
        except Exception:
            logger.exception(
                "stream Exception request_id=%s conversation_id=%s",
                request_id,
                request.conversation_id,
            )
            db.rollback()
            yield _format_sse(
                "error",
                {
                    "message": (
                        "The assistant response could not be completed. "
                        "No assistant message was saved."
                    )
                },
            )
            raise
        finally:
            logger.info(
                "generator exits request_id=%s conversation_id=%s",
                request_id,
                request.conversation_id,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
