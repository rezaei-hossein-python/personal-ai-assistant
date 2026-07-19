try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - depends on environment
    OpenAI = None

from app.config import settings


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
):

    conversation = []

    if memories:

        memory_text = "\n".join(
            [
                f"{memory.key}: {memory.value}"
                for memory in memories
            ]
        )

        conversation.append(
            {
                "role": "system",
                "content": (
                    "Known user information:\n"
                    f"{memory_text}"
                )
            }
        )


    for item in history:

        conversation.append(
            {
                "role": item["role"],
                "content": item["content"],
            }
        )


    conversation.append(
        {
            "role": "user",
            "content": message,
        }
    )


    client = _get_client()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=conversation,
    )


    return response.output_text