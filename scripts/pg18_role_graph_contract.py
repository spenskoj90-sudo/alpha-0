"""Offline PG18 role dependency graph parity (NOT source, dump, or restore proof).

Requires separately authenticated source/target snapshots using opaque aliases.
No SQL, credentials, networking, row data, or sensitive values are read here.
The caller must privately control alias maps and ensure the aliases are truly
anonymized. CLI output never contains any provided identifiers.
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
PUBLIC = "PUBLIC"
ROLE_FLAGS = ("login", "bypass_rls", "superuser", "createdb", "createrole",
              "replication", "inherit")
ROLE_FIELDS = frozenset(("id", "connection_limit", *ROLE_FLAGS))
# member, granted role, membership grantor, ADMIN, INHERIT, SET (PostgreSQL >=16).
# Object ACLs include grantor, grantee, privilege and grant option.
EDGE_SPECS = {
    "membership": ("role", "role", "role", "bool", "bool", "bool"),
    "ownership": ("object", "role"),
    "acl": ("object", "role", "grantee", "privilege", "bool"),
    "default_acl": ("object", "role", "role", "grantee", "privilege", "bool"),
    "policy": ("object", "grantee"),
}
PRIVILEGES = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE",
                        "REFERENCES", "TRIGGER", "USAGE", "CREATE", "EXECUTE",
                        "CONNECT", "TEMPORARY", "MAINTAIN", "SET", "ALTER SYSTEM"})


class GraphRejected(ValueError):
    """Security error; messages must never include user inputs."""


def _fail(message: str) -> None:
    raise GraphRejected(message)


def _snapshot(snapshot: Any) -> tuple[dict, dict]:
    if type(snapshot) is not dict or set(snapshot) != {"pg_major", "roles", "edges"}:
        _fail("unexpected role graph fields")
    if type(snapshot["pg_major"]) is not int or snapshot["pg_major"] != 18:
        _fail("PostgreSQL 18 expected")
    roles = snapshot["roles"]
    if type(roles) is not list or not roles or len(roles) > 512:
        _fail("bounded nonempty role list expected")
    role_dict = {}
    for role in roles:
        if type(role) is not dict or set(role) != ROLE_FIELDS:
            _fail("incomplete role capability manifest")
        ident = role["id"]
        if type(ident) is not str or not ROLE_ID.fullmatch(ident) or ident in role_dict:
            _fail("invalid or repeated role alias")
        if any(type(role[k]) is not bool for k in ROLE_FLAGS):
            _fail("role capability flags must be boolean")
        conn_limit = role["connection_limit"]
        if type(conn_limit) is not int or not -1 <= conn_limit <= 2147483647:
            _fail("invalid connection limit")
        role_dict[ident] = tuple(role[k] for k in ROLE_FLAGS) + (conn_limit,)
    edges = snapshot["edges"]
    if type(edges) is not dict or set(edges) != set(EDGE_SPECS):
        _fail("all five relation categories required")
    normalized = {}
    for category, pattern in EDGE_SPECS.items():
        items = edges[category]
        if type(items) is not list or len(items) > 10000:
            _fail("invalid dependency list")
        checked = []
        for edge in items:
            if type(edge) is not list or len(edge) != len(pattern):
                _fail("invalid dependency structure")
            for value, kind in zip(edge, pattern):
                if kind == "bool":
                    if type(value) is not bool:
                        _fail("membership or grant options must be boolean")
                elif kind == "role":
                    if type(value) is not str or value not in role_dict:
                        _fail("unmapped role dependency")
                elif kind == "grantee":
                    if type(value) is not str or (value != PUBLIC and value not in role_dict):
                        _fail("unmapped grant or policy subject")
                elif kind == "object":
                    if type(value) is not str or not OBJECT_ID.fullmatch(value):
                        _fail("non-opaque object identifier")
                elif kind == "privilege":
                    if type(value) is not str or value not in PRIVILEGES:
                        _fail("invalid privilege")
            if category == "membership" and edge[0] == edge[1]:
                _fail("self-membership is invalid")
            if category in {"acl", "default_acl"} and edge[-3] == PUBLIC and edge[-1]:
                _fail("PUBLIC cannot receive a grant option")
            checked.append(tuple(edge))
        if len(checked) != len(set(checked)):
            _fail("duplicate dependency")
        normalized[category] = set(checked)
    return role_dict, normalized


def compare_role_graphs(source: Any, restored: Any, mapping: Any) -> tuple[str, ...]:
    """Pure structural comparison, never actual role or restore acceptance."""
    src_roles, src_edges = _snapshot(source)
    dst_roles, dst_edges = _snapshot(restored)
    if type(mapping) is not dict or set(mapping) != {"role_map"}:
        _fail("explicit role mapping required")
    remap = mapping["role_map"]
    if type(remap) is not dict or set(remap) != set(src_roles):
        _fail("every source role must be mapped")
    if any(type(src) is not str or type(dst) is not str or dst not in dst_roles
           for src, dst in remap.items()):
        _fail("unrecognized destination role")
    if len(set(remap.values())) != len(remap) or set(remap.values()) != set(dst_roles):
        _fail("missing, collapsed or extra target role")
    differences = []
    if any(src_roles[src] != dst_roles[dst] for src, dst in remap.items()):
        differences.append("role_capabilities")
    for category, pattern in EDGE_SPECS.items():
        expected = {
            tuple(remap[value] if kind == "role"
                  else (value if value == PUBLIC else remap[value]) if kind == "grantee"
                  else value for value, kind in zip(edge, pattern))
            for edge in src_edges[category]
        }
        if expected != dst_edges[category]:
            differences.append(category)
    return tuple(differences)


def _read(path: str) -> Any:
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 131072:
        _fail("small regular private manifest required")
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Offline role graph contract; NOT restore proof")
    ap.add_argument("source")
    ap.add_argument("isolated_target")
    ap.add_argument("role_mapping")
    args = ap.parse_args(argv)
    try:
        differences = compare_role_graphs(_read(args.source), _read(args.isolated_target),
                                          _read(args.role_mapping))
    except (OSError, UnicodeError, json.JSONDecodeError, GraphRejected):
        print("ROLE_GRAPH_PREFLIGHT_REJECTED; NOT_RESTORE_PASS", file=sys.stderr)
        return 2
    if differences:
        print("ROLE_GRAPH_MISMATCH: " + ",".join(differences) + "; NOT_RESTORE_PASS")
        return 1
    print("ROLE_GRAPH_STRUCTURAL_MATCH; NOT_DUMP_PASS; NOT_RESTORE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
