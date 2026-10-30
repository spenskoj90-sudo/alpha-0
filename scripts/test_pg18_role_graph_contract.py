"""Offline PG18 role graph tests; all data is synthetic and credential-free."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from pg18_role_graph_contract import GraphRejected, compare_role_graphs, main


def role(ident, **kw):
    r = dict(id=ident, login=False, bypass_rls=False, superuser=False,
             createdb=False, createrole=False, replication=False,
             inherit=True, connection_limit=-1)
    r.update(kw)
    return r


def graph(prefix="r"):
    a, b, c = (prefix + s for s in ("01", "02", "03"))
    return {"pg_major": 18,
            "roles": [role(a, login=True, connection_limit=4),
                      role(b, bypass_rls=True), role(c)],
            "edges": {
                "membership": [[a, b, c, False, True, True]],
                "ownership": [["o_public_schema", b], ["o_auth_table", c]],
                "acl": [["o_auth_table", b, a, "SELECT", False],
                        ["o_public_schema", b, "PUBLIC", "USAGE", False]],
                "default_acl": [["o_public_defaults", b, b, a, "SELECT", True]],
                "policy": [["o_rls_policy", a], ["o_public_policy", "PUBLIC"]],
            }}


MAP = {"role_map": {"r01": "t01", "r02": "t02", "r03": "t03"}}


class GraphContractTests(unittest.TestCase):
    def test_explicit_mapping_and_extended_edges_match(self):
        self.assertEqual(compare_role_graphs(graph(), graph("t"), MAP), ())

    def test_missing_mapping_and_role_collapse_rejected(self):
        for bad in (dict(r01="t01", r02="t02"),
                    dict(r01="t01", r02="t02", r03="t02")):
            with self.subTest(bad=bad), self.assertRaises(GraphRejected):
                compare_role_graphs(graph(), graph("t"), {"role_map": bad})

    def test_target_extra_role_rejected(self):
        d = graph("t"); d["roles"].append(role("t04"))
        with self.assertRaises(GraphRejected):
            compare_role_graphs(graph(), d, MAP)

    def test_ownership_drift_detected(self):
        d = graph("t"); d["edges"]["ownership"].pop()
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("ownership",))

    def test_each_edge_class_drift_detected(self):
        for category in ("membership", "acl", "default_acl", "policy"):
            d = graph("t"); d["edges"][category] = []
            with self.subTest(category=category):
                self.assertEqual(compare_role_graphs(graph(), d, MAP), (category,))

    def test_membership_admin_option_privilege_escalation(self):
        d = graph("t"); d["edges"]["membership"][0][3] = True
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("membership",))

    def test_membership_set_option_drift(self):
        d = graph("t"); d["edges"]["membership"][0][5] = False
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("membership",))

    def test_membership_inherit_option_drift(self):
        d = graph("t"); d["edges"]["membership"][0][4] = False
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("membership",))

    def test_membership_grantor_drift(self):
        d = graph("t"); d["edges"]["membership"][0][2] = "t02"
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("membership",))

    def test_object_acl_grant_option_drift(self):
        d = graph("t"); d["edges"]["acl"][0][-1] = True
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("acl",))

    def test_default_acl_grantor_and_grant_option_drift(self):
        for idx, value in ((2, "t03"), (5, False)):
            d = graph("t"); d["edges"]["default_acl"][0][idx] = value
            with self.subTest(index=idx):
                self.assertEqual(compare_role_graphs(graph(), d, MAP), ("default_acl",))

    def test_acl_grant_to_public_must_not_be_grantable(self):
        d = graph(); d["edges"]["acl"][1][-1] = True
        with self.assertRaises(GraphRejected):
            compare_role_graphs(d, graph("t"), MAP)

    def test_public_is_not_a_membership_role_or_grantor(self):
        for category, index in (("membership", 1), ("acl", 1)):
            d = graph(); d["edges"][category][0][index] = "PUBLIC"
            with self.subTest(category=category), self.assertRaises(GraphRejected):
                compare_role_graphs(d, graph("t"), MAP)

    def test_role_flag_escalations_detected(self):
        for flag in ("login", "bypass_rls", "superuser", "createdb", "createrole",
                     "replication", "inherit"):
            d = graph("t")
            d["roles"][2][flag] = not d["roles"][2][flag]
            with self.subTest(flag=flag):
                self.assertEqual(compare_role_graphs(graph(), d, MAP), ("role_capabilities",))

    def test_connection_limit_drift_detected(self):
        d = graph("t"); d["roles"][0]["connection_limit"] = -1
        self.assertEqual(compare_role_graphs(graph(), d, MAP), ("role_capabilities",))

    def test_invalid_connection_limit_and_role_types_rejected(self):
        for val in (True, "-1", -2, 2147483648):
            d = graph(); d["roles"][0]["connection_limit"] = val
            with self.subTest(val=val), self.assertRaises(GraphRejected):
                compare_role_graphs(d, graph("t"), MAP)

    def test_malformed_extra_fields_and_pii_rejected(self):
        for key in ("email", "password", "rows"):
            d = graph(); d[key] = "fake-not-real"
            with self.subTest(key=key), self.assertRaises(GraphRejected):
                compare_role_graphs(d, graph("t"), MAP)
        d = graph(); d["roles"][0]["name"] = "unwanted"
        with self.assertRaises(GraphRejected):
            compare_role_graphs(d, graph("t"), MAP)

    def test_missing_new_pg18_required_role_flag_rejected(self):
        d = graph(); del d["roles"][0]["replication"]
        with self.assertRaises(GraphRejected):
            compare_role_graphs(d, graph("t"), MAP)

    def test_wrong_version_boolean_int_and_self_member_rejected(self):
        for change in (lambda d: d.update(pg_major=17),
                       lambda d: d["roles"][0].update(login=1),
                       lambda d: d["edges"]["membership"][0].__setitem__(1, "r01"),
                       lambda d: d["edges"]["membership"][0].__setitem__(4, 1)):
            d = graph(); change(d)
            with self.assertRaises(GraphRejected):
                compare_role_graphs(d, graph("t"), MAP)

    def test_duplicate_edges_rejected(self):
        d = graph(); d["edges"]["acl"].append(list(d["edges"]["acl"][0]))
        with self.assertRaises(GraphRejected):
            compare_role_graphs(d, graph("t"), MAP)

    def test_dangling_grantor_role_rejected(self):
        d = graph(); d["edges"]["acl"][0][1] = "r99"
        with self.assertRaises(GraphRejected):
            compare_role_graphs(d, graph("t"), MAP)

    def test_cli_never_prints_identifiers_or_restore_pass(self):
        with tempfile.TemporaryDirectory() as td:
            fs = [Path(td) / f"i{i}.json" for i in range(3)]
            for p, d in zip(fs, [graph(), graph("t"), MAP]):
                p.write_text(json.dumps(d), encoding="utf-8")
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(list(map(str, fs))), 0)
            self.assertEqual(out.getvalue().strip(),
                             "ROLE_GRAPH_STRUCTURAL_MATCH; NOT_DUMP_PASS; NOT_RESTORE_PASS")
            d = graph("t"); d["edges"]["acl"][0][-1] = True
            fs[1].write_text(json.dumps(d), encoding="utf-8")
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(list(map(str, fs))), 1)
            self.assertNotIn("t01", out.getvalue())
            err = StringIO(); fs[0].write_text('{not_json', encoding="utf-8")
            with redirect_stderr(err):
                self.assertEqual(main(list(map(str, fs))), 2)
            self.assertNotIn("{not_json", err.getvalue())


if __name__ == "__main__":
    unittest.main()
