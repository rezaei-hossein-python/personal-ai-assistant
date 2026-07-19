from openai import OpenAI

from app.config import settings


client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


def extract_memory(message: str):

    prompt = f"""
You are a memory extraction system.

Analyze the user message below.

Only extract information that should be remembered for future conversations.

Examples:
- preferences
- name
- job
- skills
- hobbies
- important personal facts

Do not extract:
- questions
- temporary requests
- explanations
- general knowledge

Return ONLY valid JSON.

Format:

{{
    "remember": true,
    "category": "preference",
    "key": "programming_language",
    "value": "Python"
}}

If nothing should be remembered:

{{
    "remember": false
}}

User message:

{message}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text