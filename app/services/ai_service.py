from openai import OpenAI

from app.config import settings
from app.core.logging import logger


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def ask_ai(message: str):
    logger.info("Sending request to OpenAI")

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=message
    )

    logger.info("OpenAI response received")

    return response.output_text