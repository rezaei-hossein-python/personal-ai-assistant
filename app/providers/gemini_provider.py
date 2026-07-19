from app.config import settings
from app.providers.http import post_json
from app.providers.model_provider import (
    ModelCapabilities,
    ModelProvider,
    ProviderAvailabilityError,
)


class GeminiModelProvider(ModelProvider):
    provider_name = "gemini"

    @property
    def generation_model(self) -> str:
        return settings.GEMINI_MODEL

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            structured_output=True,
            long_context=True,
            multimodal=True,
        )

    @property
    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def generate(self, messages: list[dict]) -> str:
        if not self.is_configured:
            raise ProviderAvailabilityError("GEMINI_API_KEY is not configured")

        text = "\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in messages
        )
        response = post_json(
            url=(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.generation_model}:generateContent"
                f"?key={settings.GEMINI_API_KEY}"
            ),
            headers={},
            payload={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": text}],
                    }
                ]
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
        candidates = response.get("candidates") or []
        if not candidates:
            raise ProviderAvailabilityError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts") or []
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        if not text_parts:
            raise ProviderAvailabilityError("Gemini returned no text")
        return "\n".join(text_parts)
