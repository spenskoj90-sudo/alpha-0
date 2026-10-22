import json

import pytest
from pydantic import ValidationError

from app.core.game_capability_catalog import catalog
from app.core.game_source_modules import source_modules, validate_source_modules

from app.core.game_source_modules import SOURCE_MAP


def payload():
    return json.loads(SOURCE_MAP.read_text())


def validate(raw):
    return validate_source_modules(json.dumps(raw).encode(), catalog())


def test_wow_checkpoint_and_android_ocr_are_never_presented_as_verified():
    report = source_modules()
    assert report["execution_authority"] is False
    profiles = {p["profile_id"]: p for p in report["profiles"]}
    assert set(profiles) == {"world-of-warcraft-windows", "shattered-pixel-dungeon-android"}
    wow = profiles["world-of-warcraft-windows"]
    android = profiles["shattered-pixel-dungeon-android"]
    for profile in profiles.values():
        assert profile["exact_environment_status"] == "l3_pending"
        for field in profile["fields"]:
            assert field["availability"] == "UNKNOWN"
            assert field["verified_freshness_ms"] is None
            assert field["measured_latency_ms"] is None
            assert field["confidence"] is None
        for module in profile["modules"]:
            assert module["readiness"] == "WAITING_FOR_VERIFIED_SOURCE"
            assert module["execution_authority"] is False
            assert module["available_signals"] == []
            assert module["missing_signals"] == module["fields"]
            assert "actions" not in module
    assert wow["fields"][0]["status"] == "checkpoint_unverified"
    assert android["fields"][0]["status"] == "uncalibrated_candidate"
    assert {m["id"] for m in wow["modules"]} == {"combat", "character_build", "economy"}
    for profile in profiles.values():
        assert profile["shared_player_state"] == {
            "schema_version": 1, "availability": "UNKNOWN",
            "session_binding": None, "last_updated_ms": None,
        }
        for module in profile["modules"]:
            assert module["module_contract_version"] == 1
            assert module["module_version"] == "1.0.0"
            assert module["shared_state_schema_version"] == 1
            assert module["lifecycle_status"] == "NOT_STARTED"
            assert module["outputs_available"] == []
            assert module["dependencies"] == []
            assert module["outputs"]
    assert next(m for m in wow["modules"] if m["id"] == "combat")["lifecycle"] == "checkpoint_bound"
    assert next(m for m in android["modules"] if m["id"] == "combat")["lifecycle"] == "session_bound"



def test_contract_readback_is_independent():
    one = source_modules()
    one["profiles"][0]["fields"].clear()
    assert len(source_modules()["profiles"][0]["fields"]) == 6


@pytest.mark.parametrize("mutate,expected", [
    (lambda x: x["profiles"][0].update(profile_id="different"), "SOURCE_EXACT_PROFILE_MISMATCH"),
    (lambda x: x["profiles"][0].update(patch="3.3.5"), "SOURCE_EXACT_PROFILE_MISMATCH"),
    (lambda x: x["profiles"][0]["fields"][0].update(source_type=None), "SOURCE_STATUS_INVALID"),
    (lambda x: x["profiles"][0]["fields"][0].update(provenance=[]), "SOURCE_PROVENANCE_MISSING"),
    (lambda x: x["profiles"][0]["fields"][0].update(provenance=["source:invented"]), "SOURCE_UNDECLARED_PROVENANCE"),
    (lambda x: x["profiles"][0]["modules"][0].update(fields=["missing"]), "SOURCE_UNDECLARED_FIELD"),
    (lambda x: x["profiles"][0]["fields"].append(x["profiles"][0]["fields"][0].copy()), "SOURCE_DUPLICATE_ID"),
])
def test_mismatched_or_invented_source_boundaries_are_rejected(mutate, expected):
    data = payload()
    mutate(data)
    with pytest.raises((ValueError, ValidationError), match=expected):
        validate(data)


@pytest.mark.parametrize("field", ["actions", "execution_authority", "entitlements", "executor"])
def test_modules_cannot_acquire_action_authority_from_data(field):
    data = payload()
    data["profiles"][0]["modules"][0][field] = ["advance"]
    with pytest.raises(ValidationError):
        validate(data)


def test_malformed_bytes_and_unknown_catalog_profiles_fail_closed():
    with pytest.raises(ValueError, match="SOURCE_MAP_SIZE_INVALID"):
        validate_source_modules(b"", catalog())
    with pytest.raises(ValueError, match="SOURCE_MAP_SIZE_INVALID"):
        validate_source_modules(b" " * 65537, catalog())
    data = payload()
    data["profiles"][0]["game"] = "other-game"
    with pytest.raises(ValueError, match="SOURCE_EXACT_PROFILE_MISMATCH"):
        validate(data)


@pytest.mark.parametrize("mutate,expected", [
    (lambda x: x["profiles"][0]["modules"][0].update(module_contract_version=2), "literal"),
    (lambda x: x["profiles"][0]["modules"][0].update(module_version="1.0"), "string_too_short"),
    (lambda x: x["profiles"][0]["modules"][0].update(module_version="01.0.0"), "string_pattern_mismatch"),
    (lambda x: x["profiles"][0]["modules"][0].update(shared_state_schema_version=2), "literal"),
    (lambda x: x["profiles"][0]["modules"][0].update(lifecycle="session_bound"), "SOURCE_LIFECYCLE_INVALID"),
    (lambda x: x["profiles"][1]["modules"][0].update(lifecycle="checkpoint_bound"), "SOURCE_LIFECYCLE_INVALID"),
    (lambda x: x["profiles"][0]["modules"][0].update(lifecycle="permanent"), "literal"),
    (lambda x: x["profiles"][0]["modules"][0].update(dependencies=["missing"]), "SOURCE_MODULE_DEPENDENCY_INVALID"),
    (lambda x: x["profiles"][0]["modules"][0].update(dependencies=["combat"]), "SOURCE_MODULE_DEPENDENCY_INVALID"),
    (lambda x: x["profiles"][0]["modules"][0].update(dependencies=["economy", "economy"]), "SOURCE_DUPLICATE_DEPENDENCY"),
    (lambda x: x["profiles"][1]["modules"][0].update(dependencies=["economy"]), "SOURCE_MODULE_DEPENDENCY_INVALID"),
    (lambda x: x["profiles"][0]["modules"][0].update(outputs=["economy_context"]), "SOURCE_PRESENTATION_MISMATCH"),
    (lambda x: x["profiles"][0]["modules"][0].update(outputs=["recommendation_context", "recommendation_context"]), "SOURCE_DUPLICATE_PRESENTATION"),
    (lambda x: x["profiles"][0]["modules"][0].update(ui_surfaces=["recommendations", "recommendations"]), "SOURCE_DUPLICATE_PRESENTATION"),
    (lambda x: x["profiles"][0]["modules"][0].update(outputs=["game_command"]), "literal"),
    (lambda x: x["profiles"][0]["modules"][0].pop("module_version"), "Field required"),
])
def test_versioned_module_contract_denies_invalid_lifecycle_or_actions(mutate, expected):
    value = payload()
    mutate(value)
    with pytest.raises((ValueError, ValidationError), match=expected):
        validate(value)


def test_module_dependencies_must_form_acyclic_exact_profile_graph():
    data = payload()
    combat, character, economy = data["profiles"][0]["modules"]
    combat["dependencies"] = ["character_build"]
    economy["dependencies"] = ["combat"]
    # DAG is permitted but no dependency is inferred to be ready from registration.
    parsed = validate(data)
    assert parsed.profiles[0].modules[0].dependencies == ("character_build",)
    character["dependencies"] = ["economy"]
    with pytest.raises(ValueError, match="SOURCE_MODULE_CYCLE"):
        validate(data)


def test_different_domains_share_schema_but_no_live_game_state_or_action_grant():
    profiles = {p["profile_id"]: p for p in source_modules()["profiles"]}
    wow = profiles["world-of-warcraft-windows"]
    android = profiles["shattered-pixel-dungeon-android"]
    for profile, module_id in ((wow, "economy"), (android, "combat")):
        module = next(m for m in profile["modules"] if m["id"] == module_id)
        assert module["outputs_available"] == []
        assert module["available_signals"] == []
        assert module["readiness"] == "WAITING_FOR_VERIFIED_SOURCE"
        assert module["lifecycle_status"] == "NOT_STARTED"
        assert module["execution_authority"] is False
        assert profile["shared_player_state"]["session_binding"] is None
