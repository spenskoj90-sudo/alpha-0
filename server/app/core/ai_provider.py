from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol

AIResultKind = Literal["fact", "inference", "recommendation"]


@dataclass(frozen=True, slots=True)
class AIProviderResult:
    """Provider-neutral AI output with explicit evidence metadata.

    The result is observational data only. It does not authorize an operation
    or represent an instruction for an executor.
    """

    kind: AIResultKind
    text: str
    confidence: float
    provenance: tuple[str, ...]
    provider_id: str
    model_id: str

    def __post_init__(self) -> None:
        if not self.text or len(self.text) > 2000:
            raise ValueError("AI_RESULT_TEXT_INVALID")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("AI_RESULT_CONFIDENCE_INVALID")
        if not self.provenance or len(self.provenance) > 20:
            raise ValueError("AI_RESULT_PROVENANCE_INVALID")
        if any(not item or len(item) > 256 for item in self.provenance):
            raise ValueError("AI_RESULT_PROVENANCE_INVALID")
        if not self.provider_id or len(self.provider_id) > 128:
            raise ValueError("AI_RESULT_PROVIDER_INVALID")
        if not self.model_id or len(self.model_id) > 128:
            raise ValueError("AI_RESULT_MODEL_INVALID")


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


class BaselineRecommendationProvider:
    """Deterministic local provider preserving the current baseline behavior."""

    provider_id = "sentinel-core"
    model_id = "context-baseline-v1"

    def generate(self, context: Mapping[str, Any]) -> AIProviderResult:
        # Context is intentionally not interpolated into the output. This keeps
        # the baseline deterministic and prevents accidental data disclosure.
        del context
        return AIProviderResult(
            kind="recommendation",
            text="Review the most recent character events before making a progression decision.",
            confidence=0.72,
            provenance=("sentinel-core:context-baseline",),
            provider_id=self.provider_id,
            model_id=self.model_id,
        )
