from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sentinel_orchestration", ROOT / "scripts/sentinel_orchestration.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)

def main():
    value = json.loads((ROOT / "automation/orchestration-lanes.example.json").read_text(encoding="utf-8"))
    payload = module.run(value)
    assert payload["status"] == "SUCCESS"
    assert payload["laneCount"] == 2
    assert payload["parallelWorkers"] == 2
    assert all(lane["mode"] == "read_only" for lane in payload["lanes"])
    print("orchestration harness tests: PASS")

if __name__ == "__main__":
    main()
