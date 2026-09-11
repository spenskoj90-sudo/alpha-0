from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class AIProviderResult:
    kind: str
    text: str
    confidence: float
    provenance: tuple[str, ...]
    provider_id: str
    model_id: str


class AIProvider(Protocol):
    provider_id: str
    model_id: str

    def generate(self, context: Mapping[str, Any]) -> AIProviderResult:
        """Produce a bounded observational result from normalized context."""


class AIProviderRegistry:
    """Explicit provider registry with deterministic, fail-closed routing."""

    def __init__(self, providers: tuple[AIProvider, ...] = (), default_provider_id: str | None = None) -> None:
        self._providers: dict[str, AIProvider] = {}
        for provider in providers:
            self.register(provider)
        self._default_provider_id = default_provider_id
        if default_provider_id is not None and default_provider_id not in self._providers:
            raise ValueError("AI_DEFAULT_PROVIDER_NOT_REGISTERED")

    def register(self, provider: AIProvider) -> None:
        provider_id = provider.provider_id.strip()
        if not provider_id:
            raise ValueError("AI_PROVIDER_ID_REQUIRED")
        if provider_id in self._providers:
            raise ValueError("AI_PROVIDER_ALREADY_REGISTERED")
        self._providers[provider_id] = provider

    def set_default(self, provider_id: str) -> None:
        if provider_id not in self._providers:
            raise KeyError("AI_PROVIDER_NOT_REGISTERED")
        self._default_provider_id = provider_id

    def route(self, provider_id: str | None = None) -> AIProvider:
        selected = provider_id or self._default_provider_id
        if not selected:
            raise RuntimeError("AI_PROVIDER_NOT_CONFIGURED")
        provider = self._providers.get(selected)
        if provider is None:
            raise KeyError("AI_PROVIDER_NOT_REGISTERED")
        return provider

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def describe(self) -> tuple[dict[str, str | bool], ...]:
        """Return bounded provider metadata without exposing credentials/config."""
        return tuple(
            {
                "provider_id": provider_id,
                "model_id": self._providers[provider_id].model_id,
                "default": provider_id == self._default_provider_id,
            }
            for provider_id in sorted(self._providers)
        )


class BaselineRecommendationProvider:
    """Deterministic local provider preserving the current baseline behavior."""

    provider_id = "sentinel-core"
    model_id = "context-baseline-v1"

    def generate(self, context: Mapping[str, Any]) -> AIProviderResult:
        del context
        return AIProviderResult(
            kind="recommendation",
            text="Review the most recent character events before making a progression decision.",
            confidence=0.72,
            provenance=("sentinel-core:context-baseline",),
            provider_id=self.provider_id,
            model_id=self.model_id,
        )
