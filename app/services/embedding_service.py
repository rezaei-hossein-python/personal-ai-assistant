from abc import ABC, abstractmethod

from app.config import settings
from app.core.embedding import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSION


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed") from exc

        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(
            model=DEFAULT_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding


def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider()
