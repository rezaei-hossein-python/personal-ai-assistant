from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime | None = None


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    message_count: int = 0
    first_user_message: str | None = None


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: list[ConversationMessageResponse]
