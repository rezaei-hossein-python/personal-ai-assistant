try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - depends on environment
    OpenAI = None

from app.config import settings
from app.services.prompt_service import build_chat_messages


def _get_client():
    if OpenAI is None:
        raise RuntimeError("The openai package is not installed")

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def ask_ai(
    message: str,
    history: list,
    memories: list = None,
    document_chunks: list = None,
):
    conversation = build_chat_messages(
        message=message,
        history=history,
        memories=memories,
        document_chunks=document_chunks,
    )


    client = _get_client()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=conversation,
    )


    return response.output_text
