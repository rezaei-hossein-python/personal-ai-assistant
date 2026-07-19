from app.config import settings
from app.providers.http import post_json
from app.providers.model_provider import (
    ModelCapabilities,
    ModelProvider,
    ProviderAvailabilityError,
)


class XAIModelProvider(ModelProvider):
    provider_name = "xai"

    @property
    def generation_model(self) -> str:
        return settings.XAI_MODEL

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            structured_output=True,
            realtime_context=True,
        )

    @property
    def is_configured(self) -> bool:
        return bool(settings.XAI_API_KEY)

    def generate(self, messages: list[dict]) -> str:
        if not self.is_configured:
            raise ProviderAvailabilityError("XAI_API_KEY is not configured")

        response = post_json(
            url="https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.XAI_API_KEY}",
            },
            payload={
                "model": self.generation_model,
                "messages": messages,
            },
        )
        return self._extract_text(response)

    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        return self.generate([{"role": "user", "content": prompt}])

    def _extract_text(self, response: dict) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise ProviderAvailabilityError("xAI returned no choices")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise ProviderAvailabilityError("xAI returned no text")
        return content
