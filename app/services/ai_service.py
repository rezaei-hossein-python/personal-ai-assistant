from openai import OpenAI

from app.config import settings


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


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


    response = client.responses.create(
        model="gpt-4.1-mini",
        input=conversation,
    )


    return response.output_text