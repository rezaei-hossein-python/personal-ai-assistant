from __future__ import annotations

import importlib
from urllib.parse import urlparse

import httpx

from app.offline_writing.provider import (
    OfflineWritingModelMissing,
    OfflineWritingProvider,
    OfflineWritingProviderError,
    OfflineWritingProviderTimeout,
    OfflineWritingProviderUnavailable,
)


class OllamaCliOfflineWritingProvider(OfflineWritingProvider):
    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
    ):
        self._model = model
        self._base_url = _validate_loopback_base_url(base_url).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama_local_http"

    @property
    def model_identifier(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            self._ensure_model_available()
        except (
            OfflineWritingModelMissing,
            OfflineWritingProviderError,
            OfflineWritingProviderTimeout,
            OfflineWritingProviderUnavailable,
        ):
            return False
        return True

    def validate_http_runtime(self) -> None:
        for module_name in (
            "httpx",
            "httpcore",
            "anyio",
            "h11",
            "certifi",
            "idna",
            "sniffio",
        ):
            importlib.import_module(module_name)

    def ensure_model_available_for_diagnostic(self, timeout_seconds: float = 5.0) -> None:
        self._ensure_model_available(timeout_seconds=timeout_seconds)

    def revise(self, text: str, instruction: str, timeout_seconds: float) -> str:
        self._ensure_model_available(timeout_seconds=5.0)

        prompt = f"{instruction}\n\nText to revise:\n{text}"
        try:
            response = httpx.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise OfflineWritingProviderTimeout("Local revision timed out") from exc
        except httpx.RequestError as exc:
            raise OfflineWritingProviderUnavailable(
                "Ollama local API could not be reached"
            ) from exc
        if response.status_code == 404:
            raise OfflineWritingModelMissing(
                f"Configured Ollama model is missing model={self._model}"
            )
        if response.status_code != 200:
            raise OfflineWritingProviderError("Local revision request failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OfflineWritingProviderError("Local revision response was not JSON") from exc
        model_text = payload.get("response")
        if not isinstance(model_text, str):
            raise OfflineWritingProviderError("Local revision response was malformed")
        return model_text

    def _ensure_model_available(self, timeout_seconds: float = 5.0) -> None:
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=timeout_seconds)
        except httpx.TimeoutException as exc:
            raise OfflineWritingProviderTimeout("Ollama local API timed out") from exc
        except httpx.RequestError as exc:
            raise OfflineWritingProviderUnavailable("Ollama local API is unavailable") from exc
        if response.status_code != 200:
            raise OfflineWritingProviderUnavailable("Ollama local API is unavailable")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OfflineWritingProviderUnavailable("Ollama tags response was not JSON") from exc
        raw_models = payload.get("models", [])
        if not isinstance(raw_models, list):
            raise OfflineWritingProviderUnavailable("Ollama tags response was malformed")
        models = {item.get("name") for item in raw_models if isinstance(item, dict)}
        if self._model not in models:
            raise OfflineWritingModelMissing(
                f"Configured Ollama model is missing model={self._model}"
            )


def _validate_loopback_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "http":
        raise OfflineWritingProviderUnavailable("Ollama endpoint must use local HTTP")
    if parsed.username or parsed.password or parsed.path not in ("", "/"):
        raise OfflineWritingProviderUnavailable("Ollama endpoint must be a local base URL")
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise OfflineWritingProviderUnavailable("Ollama endpoint must be loopback only")
    if parsed.port is None:
        raise OfflineWritingProviderUnavailable("Ollama endpoint must include a local port")
    return base_url
