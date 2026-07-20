from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationMessageResponse,
    ConversationSummaryResponse,
)
from app.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
)


router = APIRouter(prefix="/conversations", tags=["conversations"])


def conversation_summary_response(
    conversation: Conversation,
) -> ConversationSummaryResponse:
    messages = sorted(conversation.messages, key=lambda message: message.id)
    first_user_message = next(
        (message.content for message in messages if message.role == "user"),
        None,
    )
    updated_at = max(
        (message.created_at for message in messages if message.created_at is not None),
        default=conversation.created_at,
    )

    return ConversationSummaryResponse(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=updated_at,
        message_count=len(messages),
        first_user_message=first_user_message,
    )


@router.get("", response_model=list[ConversationSummaryResponse])
def list_my_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        conversation_summary_response(conversation)
        for conversation in list_conversations(db, current_user.id)
    ]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_my_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = get_conversation(db, conversation_id, current_user.id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    summary = conversation_summary_response(conversation)
    messages = sorted(conversation.messages, key=lambda message: message.id)

    return ConversationDetailResponse(
        **summary.model_dump(),
        messages=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.delete("/{conversation_id}")
def remove_my_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation deleted"}
