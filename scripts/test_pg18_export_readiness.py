"""Offline synthetic tests: no credentials, PG connection or real rows."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path

from pg18_export_readiness import METADATA_SQL, PreflightRejected, main, validate_export_readiness

BASELINE = {'public': 44, 'neon_auth': 9}


def metadata():
    return {'pg_version_num': 180006, 'expected_database': True,
            'runtime_principal': False, 'bypass_rls': True, 'superuser': False,
            'schemas': {
                'public': {'tables': 44, 'usable': 44, 'selectable': 44, 'force_rls': 43},
                'neon_auth': {'tables': 9, 'usable': 9, 'selectable': 9, 'force_rls': 0},
            }}


class ExportReadinessTests(unittest.TestCase):
    def test_metadata_privileges_match_but_do_not_return_restore_success(self):
        self.assertIsNone(validate_export_readiness(metadata(), BASELINE))

    def test_read_only_query_has_no_customer_rows_or_credentials(self):
        self.assertIn('pg_catalog.pg_class', METADATA_SQL)
        self.assertIn('has_table_privilege', METADATA_SQL)
        for forbidden in ('pg_authid', 'neon_auth.user', 'CREATE ', 'UPDATE ', 'DELETE ', 'INSERT ',
                          'PASSWORD', 'pg_dumpall'):
            self.assertNotIn(forbidden, METADATA_SQL)

    def test_runtime_identity_rejected(self):
        d = metadata(); d['runtime_principal'] = True
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(d, BASELINE)

    def test_superuser_not_approved_by_this_contract(self):
        d = metadata(); d['superuser'] = True
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(d, BASELINE)

    def test_missing_rls_authority_rejected(self):
        d = metadata(); d['bypass_rls'] = False
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(d, BASELINE)

    def test_wrong_pg_or_database_rejected(self):
        for change in ({'pg_version_num': 170005}, {'pg_version_num': '180006'},
                       {'pg_version_num': True}, {'expected_database': False}):
            with self.subTest(change=change), self.assertRaises(PreflightRejected):
                validate_export_readiness({**metadata(), **change}, BASELINE)

    def test_missing_auth_or_unexpected_schema_rejected(self):
        for key in ('neon_auth', 'public'):
            d = metadata(); del d['schemas'][key]
            with self.subTest(key=key), self.assertRaises(PreflightRejected):
                validate_export_readiness(d, BASELINE)
        d = metadata(); d['schemas']['third_party'] = d['schemas']['public']
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(d, BASELINE)

    def test_missing_select_or_schema_usage_rejected(self):
        for key in ('selectable', 'usable'):
            d = metadata(); d['schemas']['neon_auth'][key] -= 1
            with self.subTest(key=key), self.assertRaises(PreflightRejected):
                validate_export_readiness(d, BASELINE)

    def test_baseline_mismatch_and_bad_values_rejected(self):
        for bad in (True, 0, -1, '9'):
            d = metadata(); d['schemas']['neon_auth']['tables'] = bad
            with self.subTest(value=bad), self.assertRaises(PreflightRejected):
                validate_export_readiness(d, BASELINE)
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(metadata(), {'public': 44, 'neon_auth': 10})

    def test_reject_row_fields_and_invalid_envelopes(self):
        for key in ('customer_email', 'DATABASE_URL', 'rows'):
            d = metadata(); d[key] = 'synthetic-not-real'
            with self.subTest(key=key), self.assertRaises(PreflightRejected):
                validate_export_readiness(d, BASELINE)
        d = metadata(); d['schemas']['public']['users'] = 3
        with self.assertRaises(PreflightRejected):
            validate_export_readiness(d, BASELINE)

    def test_cli_reports_not_dump_or_restore_pass(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'catalog.json'
            path.write_text(json.dumps(metadata()), encoding='utf-8')
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = main([str(path), '--public-tables', '44', '--neon-auth-tables', '9'])
            self.assertEqual(rc, 0)
            self.assertIn('NOT_DUMP_PASS; NOT_RESTORE_PASS', stdout.getvalue())
            stderr = StringIO()
            with redirect_stderr(stderr):
                rc = main([str(path), '--public-tables', '44', '--neon-auth-tables', '8'])
            self.assertEqual(rc, 2)
            self.assertNotIn('synthetic-not-real', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
