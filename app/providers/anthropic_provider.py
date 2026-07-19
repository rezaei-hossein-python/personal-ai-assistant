from app.config import settings
from app.providers.http import post_json
from app.providers.model_provider import (
    ModelCapabilities,
    ModelProvider,
    ProviderAvailabilityError,
)


class AnthropicModelProvider(ModelProvider):
    provider_name = "anthropic"

    @property
    def generation_model(self) -> str:
        return settings.ANTHROPIC_MODEL

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            structured_output=True,
            long_context=True,
        )

    @property
    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def generate(self, messages: list[dict]) -> str:
        if not self.is_configured:
            raise ProviderAvailabilityError("ANTHROPIC_API_KEY is not configured")

        system_messages = [
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        ]
        chat_messages = [
            {
                "role": (
                    "assistant"
                    if message.get("role") == "assistant"
                    else "user"
                ),
                "content": message.get("content", ""),
            }
            for message in messages
            if message.get("role") != "system"
        ]

        payload = {
            "model": self.generation_model,
            "max_tokens": 2048,
            "messages": chat_messages,
        }
        if system_messages:
            payload["system"] = "\n".join(system_messages)

        response = post_json(
            url="https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            payload=payload,
        )
        return self._extract_text(response)

    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        return self.generate([{"role": "user", "content": prompt}])

    def _extract_text(self, response: dict) -> str:
        content = response.get("content") or []
        text_parts = [
            item.get("text", "")
            for item in content
            if item.get("type") == "text" and item.get("text")
        ]
        if not text_parts:
            raise ProviderAvailabilityError("Anthropic returned no text")
        return "\n".join(text_parts)
