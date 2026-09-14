#!/usr/bin/env python3
"""Release-evidence entrypoint with the active supply-chain policy extension."""
from __future__ import annotations

import release_evidence

SUPPLY_CHAIN_WORKFLOW = "Supply Chain Evidence"
SUPPLY_CHAIN_SPEC = {
    "jobs": ("Supply-chain SBOM evidence",),
    "artifacts": ("sentinel-supply-chain-evidence-{sha}",),
}


def enable_supply_chain_evidence() -> None:
    for event, specs in release_evidence.WORKFLOW_SPECS.items():
        existing = specs.get(SUPPLY_CHAIN_WORKFLOW)
        if existing is not None and existing != SUPPLY_CHAIN_SPEC:
            raise RuntimeError(f"conflicting {SUPPLY_CHAIN_WORKFLOW!r} policy for {event}")
        specs[SUPPLY_CHAIN_WORKFLOW] = SUPPLY_CHAIN_SPEC


def main() -> int:
    enable_supply_chain_evidence()
    return release_evidence.main()


if __name__ == "__main__":
    raise SystemExit(main())
