#!/usr/bin/env python3
"""Credential-free smoke/rollback contract for the owner-operated Projects bootstrap."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_project_boards_v21.sh"

MOCK_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
path = pathlib.Path(os.environ["MOCK_GH_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
def arg(flag):
    return args[args.index(flag)+1]
def save():
    path.write_text(json.dumps(state))
if args[:2] == ["api","user"]:
    print(os.environ.get("MOCK_ACCOUNT","spenskoj90-sudo"))
elif args[:2] == ["auth","status"]:
    pass
elif args[:2] == ["project","list"]:
    print(json.dumps({"projects":state["projects"]}))
elif args[:2] == ["project","create"]:
    n = len(state["projects"])+1
    project = {"number":n,"title":arg("--title"),"public":True,
               "url":"https://github.com/users/spenskoj90-sudo/projects/"+str(n)}
    state["projects"].append(project)
    save()
    print(n if "--jq" in args else json.dumps(project))
elif args[:2] == ["project","edit"]:
    n = int(args[2])
    assert arg("--visibility") == "PRIVATE"
    next(p for p in state["projects"] if p["number"]==n)["public"] = False
    save()
elif args[:2] == ["project","view"]:
    n = int(args[2])
    p = next(p for p in state["projects"] if p["number"]==n)
    if arg("--jq") == ".public":
        print(str(p["public"]).lower())
    else:
        print("#%s %s %s PRIVATE=%s" % (p["number"],p["title"],p["url"],not p["public"]))
elif args[:2] == ["project","link"]:
    link = [int(args[2]),arg("--repo")]
    if link in state["links"]:
        print("repository already linked", file=sys.stderr)
        sys.exit(1)
    state["links"].append(link)
    save()
elif args[:2] == ["project","item-list"]:
    n = str(int(args[2]))
    print(json.dumps({"items":[{"content":{"url":u}} for u in state["items"].get(n,[])]}))
elif args[:2] == ["project","item-add"]:
    n = str(int(args[2]))
    state["items"].setdefault(n,[]).append(arg("--url"))
    save()
else:
    print("UNEXPECTED GH COMMAND: "+repr(args), file=sys.stderr)
    sys.exit(3)
'''

class PortfolioBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(prefix="gh-projects-simulated-")
        self.addCleanup(self.dir.cleanup)
        path = pathlib.Path(self.dir.name)
        self.state = path/"state.json"
        self.state.write_text(json.dumps({"projects":[],"links":[],"items":{}}))
        binpath = path/"bin"
        binpath.mkdir()
        exe = binpath/"gh"
        exe.write_text(MOCK_GH)
        exe.chmod(0o700)
        self.env = {**os.environ,
                    "PATH":str(binpath)+os.pathsep+os.environ["PATH"],
                    "MOCK_GH_STATE":str(self.state)}
    def run_script(self,*args,**changes):
        return subprocess.run(["bash",str(BOOTSTRAP),*args],
                              env={**self.env,**changes},
                              capture_output=True,text=True,timeout=30)
    def test_bash_syntax(self):
        subprocess.run(["bash","-n",str(BOOTSTRAP)],check=True)
    def test_requires_explicit_apply(self):
        result=self.run_script()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads(self.state.read_text())["projects"],[])
    def test_rejects_wrong_account(self):
        result=self.run_script("--apply",MOCK_ACCOUNT="stranger")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Wrong GitHub account",result.stderr)
        self.assertEqual(json.loads(self.state.read_text())["projects"],[])
    def test_creates_three_private_projects_and_is_idempotent(self):
        first=self.run_script("--apply")
        self.assertEqual(first.returncode,0,first.stderr)
        second=self.run_script("--apply")
        self.assertEqual(second.returncode,0,second.stderr)
        state=json.loads(self.state.read_text())
        self.assertEqual([x["title"] for x in state["projects"]],
          ["SENTINEL · Engineering","FORMA · Engineering","PROJECTS · Portfolio"])
        self.assertTrue(all(p["public"] is False for p in state["projects"]))
        self.assertEqual(len(state["links"]),4)
        self.assertEqual([len(state["items"][str(i)]) for i in (1,2,3)], [4,4,5])
    def test_refuses_ambiguous_duplicate_project_title(self):
        state=json.loads(self.state.read_text())
        state["projects"]=[{"number":1,"title":"SENTINEL · Engineering","public":False},
                           {"number":2,"title":"SENTINEL · Engineering","public":False}]
        self.state.write_text(json.dumps(state))
        result=self.run_script("--apply")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Duplicate/ambiguous",result.stderr)

if __name__ == "__main__":
    unittest.main(verbosity=2)
