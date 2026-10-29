"""Offline *count-only* PostgreSQL 18 source/restore inventory comparator.

Never connects to a database or loads customer rows. Matching counts are not
proof of identical SQL definitions, ownership, data, RLS behavior or restore.
The real G3 gate additionally needs verified independent external restoration.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCHEMAS = frozenset({"public", "neon_auth"})
COUNTERS = frozenset({
    "tables", "force_rls", "rls_policies", "foreign_keys", "functions",
    "user_triggers", "sequences", "views", "explicit_relacls",
    "default_acl_entries", "owner_groups",
})


class InventoryRejected(ValueError):
    """Invalid/incomplete metadata-only snapshot or count mismatch."""


def validate_inventory(snapshot: Any) -> dict[str, dict[str, int]]:
    if type(snapshot) is not dict or set(snapshot) != {"pg_major", "schemas"}:
        raise InventoryRejected("inventory envelope must be exact and metadata-only")
    if type(snapshot["pg_major"]) is not int or snapshot["pg_major"] != 18:
        raise InventoryRejected("PostgreSQL major 18 required")
    schemas = snapshot["schemas"]
    if type(schemas) is not dict or set(schemas) != SCHEMAS:
        raise InventoryRejected("public and neon_auth are both required")
    for name, counters in schemas.items():
        if type(counters) is not dict or set(counters) != COUNTERS:
            raise InventoryRejected("incomplete or unexpected schema counters")
        if any(type(v) is not int or v < 0 for v in counters.values()):
            raise InventoryRejected("non-negative integer counters required")
        tables = counters["tables"]
        if tables == 0:
            raise InventoryRejected("empty required schema is unacceptable")
        if (counters["force_rls"] > tables or counters["explicit_relacls"] > tables
                or counters["owner_groups"] > tables or counters["owner_groups"] == 0):
            raise InventoryRejected("inconsistent relation/owner counts")
    return schemas


def compare_inventory(source: Any, restored: Any) -> tuple[str, ...]:
    """Return ordered safe count mismatches, never RESTORE_PASS.

    Even an empty tuple means *counts only* match. Both inventories must be
    independently collected from the intended source/isolated restore target.
    Metadata equality cannot prove RLS policy definitions or data integrity.
    """
    a = validate_inventory(source)
    b = validate_inventory(restored)
    return tuple(f"{schema}.{field}" for schema in sorted(SCHEMAS)
                 for field in sorted(COUNTERS)
                 if a[schema][field] != b[schema][field])


def _read_json(path: str) -> Any:
    try:
        p = Path(path)
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 32_768:
            raise InventoryRejected("private small regular metadata file required")
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise InventoryRejected("invalid or unreadable metadata JSON") from None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: pg18_restore_inventory.py SOURCE_COUNTS.json RESTORE_COUNTS.json", file=sys.stderr)
        return 2
    try:
        missing = compare_inventory(_read_json(args[0]), _read_json(args[1]))
    except InventoryRejected as exc:
        # Intentionally never print paths, JSON bodies, SQL or account data.
        print("COUNT_ONLY_PRECHECK_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    if missing:
        print("COUNT_ONLY_PRECHECK_MISMATCH: " + ", ".join(missing))
        return 1
    print("COUNT_ONLY_PRECHECK_MATCH; NOT_RESTORE_PASS; independently verify definitions, roles, RLS, data and provider")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
