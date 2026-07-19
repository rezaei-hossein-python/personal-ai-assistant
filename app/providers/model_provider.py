from abc import ABC, abstractmethod


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
    @abstractmethod
    def embedding_model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError
