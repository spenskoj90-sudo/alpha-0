"""Read-only, exact-profile source/module inventory: never an action registry.

Catalog source descriptors are implementation hypotheses, not runtime evidence.
No source becomes verified merely because a profile or module is registered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .game_capability_catalog import catalog

SOURCE_MAP = Path(__file__).resolve().parents[1] / "data/game-source-modules.v1.json"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SignalSource(ContractModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    source_type: Literal["saved_variables", "media_projection_hud_ocr"] | None
    status: Literal["checkpoint_unverified", "uncalibrated_candidate", "unknown"]
    provenance: tuple[str, ...] = Field(max_length=8)

    @model_validator(mode="after")
    def status_matches_source(self):
        expected = {
            "saved_variables": "checkpoint_unverified",
            "media_projection_hud_ocr": "uncalibrated_candidate",
            None: "unknown",
        }
        if self.status != expected[self.source_type]:
            raise ValueError("SOURCE_STATUS_INVALID")
        if self.source_type is not None and not self.provenance:
            raise ValueError("SOURCE_PROVENANCE_MISSING")
        if any(not s or len(s) > 128 for s in self.provenance):
            raise ValueError("SOURCE_PROVENANCE_INVALID")
        return self


class DomainModule(ContractModel):
    """Versioned read-only wiring declaration, NOT a running module instance."""

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    module_contract_version: Literal[1]
    module_version: str = Field(
        min_length=5, max_length=24,
        pattern=r"^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$",
    )
    shared_state_schema_version: Literal[1]
    lifecycle: Literal["session_bound", "checkpoint_bound"]
    dependencies: tuple[str, ...] = Field(max_length=16)
    fields: tuple[str, ...] = Field(min_length=1, max_length=32)
    ui_surfaces: tuple[Literal["recommendations", "character_advice", "economy_advice"], ...] = Field(
        min_length=1, max_length=3
    )
    outputs: tuple[Literal["recommendation_context", "character_context", "economy_context"], ...] = Field(
        min_length=1, max_length=3
    )


class ExactSourceProfile(ContractModel):
    profile_id: str = Field(min_length=1, max_length=128)
    game: str = Field(min_length=1, max_length=128)
    platform: Literal["windows", "android"]
    patch: str | None = Field(max_length=64)
    environment: str = Field(min_length=1, max_length=128)
    fields: tuple[SignalSource, ...] = Field(min_length=1, max_length=64)
    modules: tuple[DomainModule, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def referenced_fields_are_declared(self):
        names = [s.id for s in self.fields]
        modules = [m.id for m in self.modules]
        if len(set(names)) != len(names) or len(set(modules)) != len(modules):
            raise ValueError("SOURCE_DUPLICATE_ID")
        source_by_id = {source.id: source for source in self.fields}
        modules_by_id = {module.id: module for module in self.modules}
        output_by_surface = {
            "recommendations": "recommendation_context",
            "character_advice": "character_context",
            "economy_advice": "economy_context",
        }
        for module in self.modules:
            if len(set(module.fields)) != len(module.fields):
                raise ValueError("SOURCE_DUPLICATE_FIELD")
            if any(field not in names for field in module.fields):
                raise ValueError("SOURCE_UNDECLARED_FIELD")
            if len(set(module.dependencies)) != len(module.dependencies):
                raise ValueError("SOURCE_DUPLICATE_DEPENDENCY")
            if any(dep not in modules_by_id or dep == module.id for dep in module.dependencies):
                raise ValueError("SOURCE_MODULE_DEPENDENCY_INVALID")
            if len(set(module.ui_surfaces)) != len(module.ui_surfaces) or len(set(module.outputs)) != len(module.outputs):
                raise ValueError("SOURCE_DUPLICATE_PRESENTATION")
            if set(module.outputs) != {output_by_surface[s] for s in module.ui_surfaces}:
                raise ValueError("SOURCE_PRESENTATION_MISMATCH")
            if any(
                source_by_id[name].source_type == "saved_variables"
                for name in module.fields
            ) and module.lifecycle != "checkpoint_bound":
                raise ValueError("SOURCE_LIFECYCLE_INVALID")
            if any(
                source_by_id[name].source_type == "media_projection_hud_ocr"
                for name in module.fields
            ) and module.lifecycle != "session_bound":
                raise ValueError("SOURCE_LIFECYCLE_INVALID")

        # Only same-profile dependencies are legal. Cycles cannot be evaluated
        # in a defined order, even when all observations remain UNKNOWN.
        finished: set[str] = set()
        visiting: set[str] = set()

        def visit(module_id: str) -> None:
            if module_id in visiting:
                raise ValueError("SOURCE_MODULE_CYCLE")
            if module_id in finished:
                return
            visiting.add(module_id)
            for dependency in modules_by_id[module_id].dependencies:
                visit(dependency)
            visiting.remove(module_id)
            finished.add(module_id)

        for module_id in modules_by_id:
            visit(module_id)
        return self


class SourceModulesContract(ContractModel):
    schema_version: Literal[1]
    profiles: tuple[ExactSourceProfile, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def unique_profiles(self):
        ids = [p.profile_id for p in self.profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("SOURCE_DUPLICATE_PROFILE")
        return self


def validate_source_modules(raw: bytes, catalog_data: dict) -> SourceModulesContract:
    if not raw or len(raw) > 65536:
        raise ValueError("SOURCE_MAP_SIZE_INVALID")
    contract = SourceModulesContract.model_validate_json(raw)
    catalog_by_id = {p["id"]: p for p in catalog_data["profiles"]}
    for source in contract.profiles:
        found = catalog_by_id.get(source.profile_id)
        if found is None or any(found[key] != getattr(source, key) for key in (
            "game", "platform", "patch", "environment"
        )):
            raise ValueError("SOURCE_EXACT_PROFILE_MISMATCH")
        if found["exact_environment_status"] != "l3_pending" or (
            found["user_confirmed_actions"] or found["deterministic_automation"]
        ):
            raise ValueError("SOURCE_ACTION_PROMOTION_FORBIDDEN")
        hypotheses = {
            (s["type"], tuple(s["provenance"])) for s in found["observation_sources"]
        }
        for field in source.fields:
            if field.source_type is not None and (field.source_type, field.provenance) not in hypotheses:
                raise ValueError("SOURCE_UNDECLARED_PROVENANCE")
    return contract


def source_modules() -> dict:
    """Fresh JSON response; no mutable global registry or inferred L3 evidence."""
    value = validate_source_modules(SOURCE_MAP.read_bytes(), catalog())
    return {
        "schema_version": 1,
        "execution_authority": False,
        "profiles": [
            {
                **profile.model_dump(mode="json"),
                "exact_environment_status": "l3_pending",
                "shared_player_state": {
                    "schema_version": 1,
                    "availability": "UNKNOWN",
                    "session_binding": None,
                    "last_updated_ms": None,
                },
                "modules": [
                    {
                        **module.model_dump(mode="json"),
                        "lifecycle_status": "NOT_STARTED",
                        "outputs_available": [],
                        "readiness": "WAITING_FOR_VERIFIED_SOURCE",
                        "available_signals": [],
                        "missing_signals": list(module.fields),
                        "execution_authority": False,
                    }
                    for module in profile.modules
                ],
                "fields": [
                    {
                        **field.model_dump(mode="json"),
                        "availability": "UNKNOWN",
                        "verified_freshness_ms": None,
                        "measured_latency_ms": None,
                        "confidence": None,
                    }
                    for field in profile.fields
                ],
            }
            for profile in value.profiles
        ],
    }
