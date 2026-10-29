"""Offline, metadata-only PG18 full-export privilege preflight (NOT a backup).

No provider connection, credentials, row access, dump, or restoration. The
caller collects an aggregate catalog-only statement through an approved read
path; this validator rejects partial/mis-scoped export authorities. Matching
metadata is a necessary condition, never proof that pg_dump actually succeeds.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Run only via a separately authorized, read-only catalog query. It returns
# aggregates/flags, never role names, row values, emails or secret material.
METADATA_SQL = """WITH relations AS (
  SELECT n.nspname AS schema_name, c.oid AS relid,
         c.relforcerowsecurity AS force_rls,
         has_schema_privilege(current_user, n.oid, 'USAGE') AS usable,
         has_table_privilege(current_user, c.oid, 'SELECT') AS selectable
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname IN ('public', 'neon_auth') AND c.relkind IN ('r', 'p')
), counts AS (
  SELECT schema_name, count(*)::int AS tables,
         count(*) FILTER (WHERE usable)::int AS usable,
         count(*) FILTER (WHERE selectable)::int AS selectable,
         count(*) FILTER (WHERE force_rls)::int AS force_rls
    FROM relations GROUP BY schema_name
)
SELECT current_setting('server_version_num')::int AS pg_version_num,
       current_database() = 'sentinel' AS expected_database,
       current_user = 'sentinel_runtime_staging' AS runtime_principal,
       (SELECT rolbypassrls FROM pg_catalog.pg_roles WHERE rolname = current_user) AS bypass_rls,
       (SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = current_user) AS superuser,
       (SELECT jsonb_object_agg(schema_name,
         jsonb_build_object('tables', tables, 'usable', usable,
                            'selectable', selectable, 'force_rls', force_rls))
          FROM counts) AS schemas;"""

SCHEMAS = frozenset({'public', 'neon_auth'})
FIELDS = frozenset({'tables', 'usable', 'selectable', 'force_rls'})
ROOT = frozenset({'pg_version_num', 'expected_database', 'runtime_principal',
                  'bypass_rls', 'superuser', 'schemas'})


class PreflightRejected(ValueError):
    """Fail-closed response: never interpolate user/provider data into error."""


def validate_export_readiness(data: Any, expected_tables: dict[str, int]) -> None:
    """Validate privilege *metadata* only, never output a full-export PASS."""
    if (type(expected_tables) is not dict or set(expected_tables) != SCHEMAS
            or any(type(v) is not int or v <= 0 for v in expected_tables.values())):
        raise PreflightRejected('independent positive schema table baselines required')
    if type(data) is not dict or set(data) != ROOT:
        raise PreflightRejected('unexpected metadata-only source envelope')
    major = data['pg_version_num']
    if type(major) is not int or major // 10000 != 18:
        raise PreflightRejected('PostgreSQL 18 required')
    if data['expected_database'] is not True:
        raise PreflightRejected('incorrect source database')
    if data['runtime_principal'] is not False or data['superuser'] is not False:
        raise PreflightRejected('application runtime or superuser is not an approved exporter')
    if data['bypass_rls'] is not True:
        raise PreflightRejected('FORCE RLS requires independently approved complete-row authority')
    schemas = data['schemas']
    if type(schemas) is not dict or set(schemas) != SCHEMAS:
        raise PreflightRejected('public and neon_auth must both be inspected')
    for schema in sorted(SCHEMAS):
        counters = schemas[schema]
        if type(counters) is not dict or set(counters) != FIELDS:
            raise PreflightRejected('invalid schema metadata fields')
        if any(type(v) is not int or v < 0 for v in counters.values()):
            raise PreflightRejected('non-negative numeric privilege counts required')
        if counters['tables'] != expected_tables[schema]:
            raise PreflightRejected('independent expected schema size does not match')
        if (counters['usable'] != counters['tables']
                or counters['selectable'] != counters['tables']
                or counters['force_rls'] > counters['tables']):
            raise PreflightRejected('incomplete schema SELECT/USAGE or invalid RLS counts')
    # Deliberately return None; there is NO DUMP_PASS / RESTORE_PASS result.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='PG18 privileges only; NEVER backup/restore proof')
    parser.add_argument('catalog_json', help='private aggregate metadata JSON, no row or secret content')
    parser.add_argument('--public-tables', type=int, required=True)
    parser.add_argument('--neon-auth-tables', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        path = Path(args.catalog_json)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
            raise PreflightRejected('small regular private metadata file required')
        data = json.loads(path.read_text(encoding='utf-8'))
        validate_export_readiness(data, {'public': args.public_tables,
                                         'neon_auth': args.neon_auth_tables})
    except (OSError, UnicodeError, json.JSONDecodeError, PreflightRejected) as exc:
        # Never print JSON, file contents, role names or secrets.
        message = str(exc) if isinstance(exc, PreflightRejected) else 'invalid catalog metadata'
        print('SOURCE_PRIVILEGE_PREFLIGHT_REJECTED: ' + message, file=sys.stderr)
        return 2
    print('SOURCE_PRIVILEGE_PREFLIGHT_MATCH; NOT_DUMP_PASS; NOT_RESTORE_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
