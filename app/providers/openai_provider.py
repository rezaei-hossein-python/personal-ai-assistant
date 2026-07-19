from app.config import settings
from app.core.embedding import DEFAULT_EMBEDDING_MODEL
from app.providers.model_provider import ModelProvider


DEFAULT_GENERATION_MODEL = "gpt-4.1-mini"


class OpenAIModelProvider(ModelProvider):
    provider_name = "openai"
    generation_model = DEFAULT_GENERATION_MODEL
    embedding_model = DEFAULT_EMBEDDING_MODEL

    def _get_client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed") from exc

        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        return OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(self, messages: list[dict]) -> str:
        response = self._get_client().responses.create(
            model=self.generation_model,
            input=messages,
        )
        return response.output_text

    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        response = self._get_client().responses.create(
            model=self.generation_model,
            input=prompt,
        )
        return response.output_text

    def embed_text(self, text: str) -> list[float]:
        response = self._get_client().embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding
