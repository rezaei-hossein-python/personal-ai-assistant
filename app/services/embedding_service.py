from abc import ABC, abstractmethod

from app.core.embedding import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSION
from app.providers.openai_provider import OpenAIModelProvider


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        return OpenAIModelProvider().embed_text(text)


def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider()
