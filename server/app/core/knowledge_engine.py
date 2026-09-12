from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

_MAX_ITEMS = 12
_MAX_TEXT = 2000


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    kind: str
    text: str
    confidence: float
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.kind not in {"fact", "inference", "recommendation"}:
            raise ValueError("KNOWLEDGE_KIND_INVALID")
        if not self.text or len(self.text) > _MAX_TEXT:
            raise ValueError("KNOWLEDGE_TEXT_INVALID")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("KNOWLEDGE_CONFIDENCE_INVALID")
        if not self.provenance or len(self.provenance) > 20:
            raise ValueError("KNOWLEDGE_PROVENANCE_INVALID")


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    items: tuple[KnowledgeItem, ...]

    @property
    def provenance(self) -> tuple[str, ...]:
        values: list[str] = []
        for item in self.items:
            for source in item.provenance:
                if source not in values:
                    values.append(source)
        return tuple(values[:20])


class KnowledgeEngine:
    """Derive bounded, deterministic knowledge from normalized recommendation context.

    This engine intentionally consumes already-normalized context. It never reads
    raw adapter payloads, grants authority, persists state, or performs network I/O.
    """

    def build(self, context: Mapping[str, Any]) -> KnowledgeSnapshot:
        items: list[KnowledgeItem] = []
        player = context.get("player")
        if isinstance(player, Mapping):
            level = player.get("level")
            if isinstance(level, int):
                items.append(
                    KnowledgeItem(
                        kind="fact",
                        text=f"Character is level {level}.",
                        confidence=1.0,
                        provenance=(f"character:level:{level}",),
                    )
                )

            alive = player.get("alive")
            if isinstance(alive, bool):
                items.append(
                    KnowledgeItem(
                        kind="fact",
                        text="Character is alive." if alive else "Character is not alive.",
                        confidence=1.0,
                        provenance=(f"character:alive:{str(alive).lower()}",),
                    )
                )

        events = context.get("events")
        if isinstance(events, list) and events:
            valid_events = [event for event in events if isinstance(event, Mapping)]
            if valid_events:
                quality = str(context.get("data_quality", "UNKNOWN")).lower()
                confidence = 0.78 if quality in {"high", "complete", "good"} else 0.64
                provenance = tuple(
                    str(event.get("event_type"))
                    for event in valid_events[:4]
                    if event.get("event_type")
                )
                if provenance:
                    items.append(
                        KnowledgeItem(
                            kind="inference",
                            text="Recent activity provides progression context.",
                            confidence=confidence,
                            provenance=tuple(f"event:{value}" for value in provenance),
                        )
                    )

        if not items:
            items.append(
                KnowledgeItem(
                    kind="inference",
                    text="Insufficient normalized game evidence is available for a specific conclusion.",
                    confidence=0.40,
                    provenance=("knowledge:insufficient-context",),
                )
            )

        return KnowledgeSnapshot(tuple(items[:_MAX_ITEMS]))


def knowledge_context(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a bounded serializable knowledge projection for provider routing."""
    snapshot = KnowledgeEngine().build(context)
    return {
        "items": [
            {
                "kind": item.kind,
                "text": item.text,
                "confidence": item.confidence,
                "provenance": list(item.provenance),
            }
            for item in snapshot.items
        ],
        "provenance": list(snapshot.provenance),
    }
