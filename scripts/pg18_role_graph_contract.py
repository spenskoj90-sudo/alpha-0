"""Offline PG18 role dependency graph equivalence (NOT a restore test).

Accepts only *opaque role/object aliases*, not credential values or role names.
Both snapshots must be collected and independently authenticated by a separate
owner-approved source/restore process; this module does no SQL or network I/O.
All printed output is constant so identifiers never leak into CI logs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROLE_ID = re.compile(r"[rt][0-9a-z_]{1,31}\Z", re.ASCII)
OBJECT_ID = re.compile(r"o[0-9a-z_]{1,63}\Z", re.ASCII)
EDGE_SPECS = {"membership": ("role", "role"),
              "ownership": ("object", "role"),
              "acl": ("object", "role", "privilege"),
              "default_acl": ("object", "role", "role", "privilege"),
              "policy": ("object", "role")}
PRIVILEGES = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE", "REFERENCES",
                        "TRIGGER", "USAGE", "CREATE", "EXECUTE", "CONNECT", "TEMPORARY"})


class GraphRejected(ValueError):
    """Never reveal source/target data in error strings."""


def _fail(message: str) -> None:
    raise GraphRejected(message)


def _snapshot(snapshot: Any) -> tuple[dict, dict]:
    if type(snapshot) is not dict or set(snapshot) != {"pg_major", "roles", "edges"}:
        _fail("unexpected role-graph envelope")
    if type(snapshot["pg_major"]) is not int or snapshot["pg_major"] != 18:
        _fail("both instances must use PostgreSQL 18")
    roles = snapshot["roles"]
    if type(roles) is not list or not roles or len(roles) > 512:
        _fail("bounded nonempty role list required")
    role_dict = {}
    for role in roles:
        if type(role) is not dict or set(role) != {"id", "login", "bypass_rls", "superuser"}:
            _fail("unexpected role capability fields")
        ident = role["id"]
        if type(ident) is not str or not ROLE_ID.fullmatch(ident) or ident in role_dict:
            _fail("invalid or duplicate opaque role identity")
        if any(type(role[k]) is not bool for k in ("login", "bypass_rls", "superuser")):
            _fail("boolean role capabilities required")
        role_dict[ident] = (role["login"], role["bypass_rls"], role["superuser"])
    edges = snapshot["edges"]
    if type(edges) is not dict or set(edges) != set(EDGE_SPECS):
        _fail("all five explicit dependency classes required")
    normalized = {}
    for category, pattern in EDGE_SPECS.items():
        items = edges[category]
        if type(items) is not list or len(items) > 10000:
            _fail("bounded dependency edge list required")
        checked = []
        for edge in items:
            if type(edge) is not list or len(edge) != len(pattern):
                _fail("invalid dependency edge shape")
            for value, kind in zip(edge, pattern):
                if type(value) is not str:
                    _fail("string-only opaque dependency identifiers required")
                if kind == "role" and value not in role_dict:
                    _fail("dependency references an unlisted role")
                if kind == "object" and not OBJECT_ID.fullmatch(value):
                    _fail("opaque object identifier required")
                if kind == "privilege" and value not in PRIVILEGES:
                    _fail("unsupported privilege label")
            if category == "membership" and edge[0] == edge[1]:
                _fail("self-membership is not a valid role dependency")
            checked.append(tuple(edge))
        if len(checked) != len(set(checked)):
            _fail("duplicate role dependency edge")
        normalized[category] = set(checked)
    return role_dict, normalized


def compare_role_graphs(source: Any, restored: Any, mapping: Any) -> tuple[str, ...]:
    """Compare graph *shapes* and role flags under an explicit injective map.

    Empty differences do not assert source provenance, dump coverage, privilege
    enforcement, RLS, app authorization, or a genuine off-provider restore.
    """
    src_roles, src_edges = _snapshot(source)
    dst_roles, dst_edges = _snapshot(restored)
    if type(mapping) is not dict or set(mapping) != {"role_map"}:
        _fail("explicit role-map envelope required")
    remap = mapping["role_map"]
    if type(remap) is not dict or set(remap) != set(src_roles):
        _fail("every source role needs one explicit destination")
    if any(type(src) is not str or type(dst) is not str or dst not in dst_roles
           for src, dst in remap.items()):
        _fail("unknown destination role")
    if len(set(remap.values())) != len(remap) or set(remap.values()) != set(dst_roles):
        _fail("role collapse, unintended extra role or missing role denied")
    differences = []
    if any(src_roles[src] != dst_roles[dst] for src, dst in remap.items()):
        differences.append("role_capabilities")
    for category, pattern in EDGE_SPECS.items():
        expected = {tuple(remap[value] if kind == "role" else value
                          for value, kind in zip(edge, pattern))
                    for edge in src_edges[category]}
        if expected != dst_edges[category]:
            differences.append(category)
    return tuple(differences)


def _read(path: str) -> Any:
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 131072:
        _fail("small regular private manifest required")
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline role graph only; NOT restore proof")
    ap.add_argument("source")
    ap.add_argument("isolated_target")
    ap.add_argument("role_mapping")
    args = ap.parse_args(argv)
    try:
        diffs = compare_role_graphs(_read(args.source), _read(args.isolated_target),
                                    _read(args.role_mapping))
    except (OSError, UnicodeError, json.JSONDecodeError, GraphRejected):
        print("ROLE_GRAPH_PREFLIGHT_REJECTED; NOT_RESTORE_PASS", file=sys.stderr)
        return 2
    if diffs:
        # Print only whitelisted category names, not any role/object aliases.
        print("ROLE_GRAPH_MISMATCH: " + ",".join(diffs) + "; NOT_RESTORE_PASS")
        return 1
    print("ROLE_GRAPH_STRUCTURAL_MATCH; NOT_DUMP_PASS; NOT_RESTORE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
