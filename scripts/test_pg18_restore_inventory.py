"""Credential-free synthetic PG18 count-only tests; never a restore drill."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from pg18_restore_inventory import InventoryRejected, compare_inventory, main


COUNTS = {
    "tables": 5, "force_rls": 4, "rls_policies": 7, "foreign_keys": 2,
    "functions": 3, "user_triggers": 1, "sequences": 1, "views": 0,
    "explicit_relacls": 5, "default_acl_entries": 2, "owner_groups": 1,
}


def fixture():
    # Deliberately synthetic numbers, not a production inventory.
    return {"pg_major": 18, "schemas": {
        "public": copy.deepcopy(COUNTS),
        "neon_auth": {**COUNTS, "force_rls": 0, "rls_policies": 0,
                      "functions": 0, "user_triggers": 0,
                      "default_acl_entries": 0, "tables": 2,
                      "explicit_relacls": 0},
    }}


class InventoryContractTests(unittest.TestCase):
    def test_matching_synthetic_counts_are_only_count_match(self):
        self.assertEqual(compare_inventory(fixture(), fixture()), ())

    def test_missing_managed_auth_schema_rejected(self):
        x = fixture()
        del x["schemas"]["neon_auth"]
        with self.assertRaises(InventoryRejected):
            compare_inventory(x, fixture())

    def test_missing_or_unknown_field_rejected(self):
        for mode in ("missing", "unknown"):
            x = fixture()
            if mode == "missing":
                del x["schemas"]["public"]["default_acl_entries"]
            else:
                x["schemas"]["public"]["customer_rows"] = 5
            with self.subTest(mode=mode), self.assertRaises(InventoryRejected):
                compare_inventory(x, fixture())

    def test_major_version_fail_closed(self):
        for version in (17, True, "18", 0):
            x = fixture()
            x["pg_major"] = version
            with self.subTest(version=version), self.assertRaises(InventoryRejected):
                compare_inventory(x, fixture())

    def test_detect_force_rls_policy_function_and_acl_regressions(self):
        x = fixture()
        y = fixture()
        for field in ("force_rls", "rls_policies", "functions", "default_acl_entries"):
            y["schemas"]["public"][field] -= 1
        self.assertEqual(set(compare_inventory(x, y)),
                         {f"public.{f}" for f in ("force_rls", "rls_policies", "functions", "default_acl_entries")})

    def test_detect_neon_auth_missing_foreign_key(self):
        x, y = fixture(), fixture()
        y["schemas"]["neon_auth"]["foreign_keys"] -= 1
        self.assertEqual(compare_inventory(x, y), ("neon_auth.foreign_keys",))

    def test_reject_invalid_counts(self):
        for bad in (True, -1, "5", None):
            x = fixture()
            x["schemas"]["public"]["tables"] = bad
            with self.subTest(value=bad), self.assertRaises(InventoryRejected):
                compare_inventory(x, fixture())

    def test_reject_inconsistent_relation_ownership(self):
        for field in ("force_rls", "explicit_relacls", "owner_groups"):
            x = fixture()
            x["schemas"]["public"][field] = 6
            with self.subTest(field=field), self.assertRaises(InventoryRejected):
                compare_inventory(x, fixture())

    def test_no_pii_or_row_data_allowed_in_envelope(self):
        x = fixture()
        x["customer_email"] = "should-not-be-sent-to-ci"
        with self.assertRaises(InventoryRejected):
            compare_inventory(x, fixture())

    def test_cli_is_unambiguously_not_restore_pass(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "source.json", Path(td) / "isolated.json"
            a.write_text(json.dumps(fixture()))
            b.write_text(json.dumps(fixture()))
            from contextlib import redirect_stdout
            from io import StringIO
            buf = StringIO()
            with redirect_stdout(buf):
                result = main([str(a), str(b)])
            self.assertEqual(result, 0)
            self.assertIn("NOT_RESTORE_PASS", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
