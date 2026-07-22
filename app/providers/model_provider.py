from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


class ProviderAvailabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelCapabilities:
    text_generation: bool = True
    structured_output: bool = False
    embeddings: bool = False
    long_context: bool = False
    multimodal: bool = False
    realtime_context: bool = False
    metadata: dict = field(default_factory=dict)


class ModelProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def generation_model(self) -> str:
        raise NotImplementedError

    @property
    def embedding_model(self) -> str:
        return ""

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()

    @property
    def is_configured(self) -> bool:
        return True

    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        raise NotImplementedError

    def stream_generate(self, messages: list[dict]) -> Iterator[str]:
        yield self.generate(messages)

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        raise NotImplementedError

    def embed_text(self, text: str) -> list[float]:
        raise ProviderAvailabilityError(
            f"{self.provider_name} does not provide embeddings"
        )
