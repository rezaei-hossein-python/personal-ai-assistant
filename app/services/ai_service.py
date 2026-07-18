from openai import OpenAI

from app.config import settings


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def ask_ai(message: str, history: list):

    conversation = []

    for item in history:
        conversation.append(
            {
                "role": item["role"],
                "content": item["content"]
            }
        )

    conversation.append(
        {
            "role": "user",
            "content": message
        }
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=conversation
    )

    return response.output_text