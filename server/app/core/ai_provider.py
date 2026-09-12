from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol

from .knowledge_engine import knowledge_context

AIResultKind = Literal["fact", "inference", "recommendation"]


@dataclass(frozen=True, slots=True)
class AIProviderResult:
    """Provider-neutral AI output with explicit evidence metadata."""

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
    """Deterministic local provider consuming the Knowledge Engine projection."""

    provider_id = "sentinel-core"
    model_id = "context-baseline-v2"

    def generate(self, context: Mapping[str, Any]) -> AIProviderResult:
        knowledge = knowledge_context(context)
        items = knowledge["items"]
        recommendation = next(
            (item for item in items if item["kind"] == "inference" and item["confidence"] >= 0.50),
            None,
        )
        if recommendation is None:
            return AIProviderResult(
                kind="recommendation",
                text="Insufficient evidence for a specific progression recommendation; review recent character events first.",
                confidence=0.40,
                provenance=tuple(knowledge["provenance"][:19]) + ("recommendation:suppressed-low-evidence",),
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        confidence = min(0.89, max(0.50, float(recommendation["confidence"]) - 0.02))
        provenance = tuple(knowledge["provenance"][:19]) + ("recommendation:progression-review",)
        return AIProviderResult(
            kind="recommendation",
            text="Review the most recent character events before making a progression decision.",
            confidence=confidence,
            provenance=provenance,
            provider_id=self.provider_id,
            model_id=self.model_id,
        )
