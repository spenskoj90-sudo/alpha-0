#!/usr/bin/env python3
"""Reproduce two distinct L2-only game module lifecycle scenarios; no game input."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.game_capability_catalog import catalog
from app.core.game_module_lifecycle_replay import ModuleLifecycleReplay, ReplayFrame
from app.core.game_source_modules import SOURCE_MAP, validate_source_modules


def main() -> int:
    profiles = {
        profile.profile_id: profile
        for profile in validate_source_modules(SOURCE_MAP.read_bytes(), catalog()).profiles
    }
    results = []
    for name, events in (
        ("world-of-warcraft-windows", [
            ("checkpoint", ("normalized_events",), 1000),
            ("session", ("player_health", "target_health", "auction_listings"), 1100),
        ]),
        ("shattered-pixel-dungeon-android", [
            ("session", ("health_candidate", "player_health"), 1000),
            ("session", ("inventory",), 1100),
        ]),
    ):
        replay = ModuleLifecycleReplay(profiles[name], session_id="synthetic-run")
        for sequence, (kind, fields, tick) in enumerate(events, 1):
            replay.observe(ReplayFrame(name, "synthetic-run", sequence, tick, fields, kind),
                           now_ms=tick)
        results.append({
            "profile": name,
            "observed": replay.snapshot(now_ms=1100),
            "expired": replay.snapshot(now_ms=6201),
        })
        replay.stop()
        results[-1]["stopped"] = replay.snapshot(now_ms=6202)
    print(json.dumps({
        "evidence": "L2_SYNTHETIC_ONLY",
        "physical_source_verified": False,
        "runtime_execution": False,
        "scenarios": results,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
