from dataclasses import dataclass, field

from app.agents.types import Intent, Plan
from app.config import settings
from app.providers.anthropic_provider import AnthropicModelProvider
from app.providers.gemini_provider import GeminiModelProvider
from app.providers.model_provider import ModelProvider, ProviderAvailabilityError
from app.providers.openai_provider import OpenAIModelProvider
from app.providers.xai_provider import XAIModelProvider


@dataclass
class ProviderFallbackEvent:
    from_provider: str
    to_provider: str
    reason: str


@dataclass
class ModelRouteResult:
    provider: ModelProvider
    preferred_provider: str
    fallback_events: list[ProviderFallbackEvent] = field(default_factory=list)
    providers_invoked: list[str] = field(default_factory=list)
    collaboration_mode: bool = False
    collaborator_providers: list[ModelProvider] = field(default_factory=list)


class ModelRouter:
    def __init__(
        self,
        providers: list[ModelProvider] | None = None,
        default_provider_name: str | None = None,
        collaboration_enabled: bool | None = None,
    ):
        self.providers = {
            provider.provider_name: provider
            for provider in (
                providers
                or [
                    OpenAIModelProvider(),
                    GeminiModelProvider(),
                    AnthropicModelProvider(),
                    XAIModelProvider(),
                ]
            )
        }
        self.default_provider_name = (
            default_provider_name
            or settings.MODEL_PROVIDER_DEFAULT
            or "openai"
        )
        self.collaboration_enabled = (
            settings.MODEL_COLLABORATION_ENABLED
            if collaboration_enabled is None
            else collaboration_enabled
        )

    def route(self, plan: Plan, message: str) -> ModelRouteResult:
        preferred_provider = self._preferred_provider_name(plan, message)
        provider, fallback_events = self._resolve_provider(preferred_provider)
        collaborator_providers = self._collaborators(plan, provider)

        return ModelRouteResult(
            provider=provider,
            preferred_provider=preferred_provider,
            fallback_events=fallback_events,
            providers_invoked=[],
            collaboration_mode=bool(collaborator_providers),
            collaborator_providers=collaborator_providers,
        )

    def generate_with_fallback(
        self,
        route: ModelRouteResult,
        messages: list[dict],
    ) -> str:
        try:
            response = route.provider.generate(messages)
            route.providers_invoked.append(route.provider.provider_name)
            return response
        except ProviderAvailabilityError as exc:
            fallback = self._fallback_provider(
                exclude={route.provider.provider_name}
            )
            route.fallback_events.append(
                ProviderFallbackEvent(
                    from_provider=route.provider.provider_name,
                    to_provider=fallback.provider_name,
                    reason=str(exc),
                )
            )
            route.provider = fallback
            response = route.provider.generate(messages)
            route.providers_invoked.append(route.provider.provider_name)
            return response

    def collaborate(
        self,
        route: ModelRouteResult,
        messages: list[dict],
    ) -> list[str]:
        analyses = []
        for provider in route.collaborator_providers:
            try:
                analyses.append(provider.generate(messages))
                route.providers_invoked.append(provider.provider_name)
            except ProviderAvailabilityError as exc:
                route.fallback_events.append(
                    ProviderFallbackEvent(
                        from_provider=provider.provider_name,
                        to_provider=route.provider.provider_name,
                        reason=str(exc),
                    )
                )
        return analyses

    def _preferred_provider_name(self, plan: Plan, message: str) -> str:
        lowered = message.lower()

        if any(term in lowered for term in ("image", "photo", "screenshot")):
            return "gemini"
        if any(term in lowered for term in ("latest", "real-time", "social")):
            return "xai"
        if (
            plan.intent == Intent.KNOWLEDGE_SEARCH
            or any(term in lowered for term in ("long-form", "analyze document"))
        ):
            return "anthropic"
        return self.default_provider_name

    def _resolve_provider(
        self,
        preferred_provider_name: str,
    ) -> tuple[ModelProvider, list[ProviderFallbackEvent]]:
        preferred = self.providers.get(preferred_provider_name)
        if preferred and self._can_generate(preferred):
            return preferred, []

        fallback = self._fallback_provider(exclude={preferred_provider_name})
        reason = "Provider is not configured or cannot generate text"
        return fallback, [
            ProviderFallbackEvent(
                from_provider=preferred_provider_name,
                to_provider=fallback.provider_name,
                reason=reason,
            )
        ]

    def _fallback_provider(self, exclude: set[str]) -> ModelProvider:
        default = self.providers.get(self.default_provider_name)
        if (
            default
            and default.provider_name not in exclude
            and self._can_generate(default)
        ):
            return default

        for provider in self.providers.values():
            if provider.provider_name not in exclude and self._can_generate(provider):
                return provider

        raise ProviderAvailabilityError("No configured model provider is available")

    def _can_generate(self, provider: ModelProvider) -> bool:
        return provider.is_configured and provider.capabilities.text_generation

    def _collaborators(
        self,
        plan: Plan,
        selected_provider: ModelProvider,
    ) -> list[ModelProvider]:
        if not self.collaboration_enabled:
            return []
        if plan.intent != Intent.COMBINED_CONTEXT:
            return []

        collaborators = []
        for provider_name in ("anthropic", "openai"):
            provider = self.providers.get(provider_name)
            if (
                provider
                and provider.provider_name != selected_provider.provider_name
                and self._can_generate(provider)
            ):
                collaborators.append(provider)
        return collaborators[:2]
