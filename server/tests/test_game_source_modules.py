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
