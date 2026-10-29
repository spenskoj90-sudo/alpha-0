"""Synthetic, credential-free tests for offline role graph parity. No SQL/Neon."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from pg18_role_graph_contract import GraphRejected, compare_role_graphs, main


def graph(prefix="r"):
    a, b, c = prefix + "01", prefix + "02", prefix + "03"
    return {"pg_major": 18,
            "roles": [{"id": a, "login": True, "bypass_rls": False, "superuser": False},
                      {"id": b, "login": False, "bypass_rls": True, "superuser": False},
                      {"id": c, "login": False, "bypass_rls": False, "superuser": False}],
            "edges": {"membership": [[a,b]],
                      "ownership": [["o_public_schema",b],["o_auth_table",c]],
                      "acl": [["o_auth_table",a,"SELECT"]],
                      "default_acl": [["o_public_defaults",b,a,"SELECT"]],
                      "policy": [["o_rls_policy",a]]}}


MAP = {"role_map":{"r01":"t01","r02":"t02","r03":"t03"}}


class GraphContractTests(unittest.TestCase):
    def test_explicit_role_mapping_and_five_dependency_edges_match(self):
        self.assertEqual(compare_role_graphs(graph(),graph("t"),MAP),())

    def test_missing_mapping_denied(self):
        m=copy.deepcopy(MAP); del m["role_map"]["r03"]
        with self.assertRaises(GraphRejected): compare_role_graphs(graph(),graph("t"),m)

    def test_role_collapse_denied(self):
        m=copy.deepcopy(MAP); m["role_map"]["r03"]="t02"
        with self.assertRaises(GraphRejected): compare_role_graphs(graph(),graph("t"),m)

    def test_extra_unmapped_role_denied(self):
        d=graph("t"); d["roles"].append({"id":"t04","login":False,"bypass_rls":False,"superuser":False})
        with self.assertRaises(GraphRejected): compare_role_graphs(graph(),d,MAP)

    def test_missing_object_ownership_is_detected(self):
        d=graph("t"); d["edges"]["ownership"].pop()
        self.assertEqual(compare_role_graphs(graph(),d,MAP),("ownership",))

    def test_grants_default_acl_policy_and_memberships_detected(self):
        for key in ("membership","acl","default_acl","policy"):
            d=graph("t"); d["edges"][key]=[]
            with self.subTest(key=key): self.assertEqual(compare_role_graphs(graph(),d,MAP),(key,))

    def test_runtime_privilege_escalation_detected(self):
        d=graph("t"); d["roles"][0]["bypass_rls"]=True
        self.assertEqual(compare_role_graphs(graph(),d,MAP),("role_capabilities",))

    def test_superuser_privilege_escalation_detected(self):
        d=graph("t"); d["roles"][0]["superuser"]=True
        self.assertEqual(compare_role_graphs(graph(),d,MAP),("role_capabilities",))

    def test_malformed_fields_and_personal_data_are_denied(self):
        for key in ("email","password","rows"):
            d=graph(); d[key]="never-real"
            with self.subTest(key=key), self.assertRaises(GraphRejected): compare_role_graphs(d,graph("t"),MAP)
        d=graph(); d["roles"][0]["name"]="real_role"
        with self.assertRaises(GraphRejected): compare_role_graphs(d,graph("t"),MAP)

    def test_dangling_role_and_duplicate_edges_denied(self):
        for altered in (lambda d:d["edges"]["acl"].append(["o_auth_table","r99","SELECT"]),
                        lambda d:d["edges"]["acl"].append(list(d["edges"]["acl"][0]))):
            d=graph(); altered(d)
            with self.assertRaises(GraphRejected): compare_role_graphs(d,graph("t"),MAP)

    def test_wrong_version_bad_boolean_and_self_membership_denied(self):
        for change in (lambda d:d.update(pg_major=17),lambda d:d["roles"][0].update(login=1),
                       lambda d:d["edges"]["membership"].append(["r01","r01"])):
            d=graph(); change(d)
            with self.assertRaises(GraphRejected): compare_role_graphs(d,graph("t"),MAP)

    def test_cli_never_prints_identifiers_or_restore_pass(self):
        with tempfile.TemporaryDirectory() as td:
            files=[Path(td)/f"x{i}.json" for i in range(3)]
            for p,data in zip(files,[graph(),graph("t"),MAP]):p.write_text(json.dumps(data))
            out=StringIO()
            with redirect_stdout(out): self.assertEqual(main(list(map(str,files))),0)
            self.assertEqual(out.getvalue().strip(),"ROLE_GRAPH_STRUCTURAL_MATCH; NOT_DUMP_PASS; NOT_RESTORE_PASS")
            d=graph("t");d["edges"]["acl"]=[];files[1].write_text(json.dumps(d))
            out=StringIO()
            with redirect_stdout(out): self.assertEqual(main(list(map(str,files))),1)
            self.assertNotIn("r01",out.getvalue())
            err=StringIO();files[0].write_text('{bad')
            with redirect_stderr(err): self.assertEqual(main(list(map(str,files))),2)
            self.assertNotIn("{bad",err.getvalue())


if __name__ == "__main__": unittest.main()
