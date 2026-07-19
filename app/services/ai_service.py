from app.providers.model_provider import ModelProvider
from app.providers.openai_provider import OpenAIModelProvider
from app.services.prompt_service import build_chat_messages


def ask_ai(
    message: str,
    history: list,
    memories: list = None,
    document_chunks: list = None,
    model_provider: ModelProvider | None = None,
):
    conversation = build_chat_messages(
        message=message,
        history=history,
        memories=memories,
        document_chunks=document_chunks,
    )


    provider = model_provider or OpenAIModelProvider()
    return provider.generate(conversation)
