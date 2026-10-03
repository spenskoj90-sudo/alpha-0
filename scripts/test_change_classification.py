#!/usr/bin/env python3
import unittest
from change_classification import classify

class ChangeClassificationTests(unittest.TestCase):
    def test_docs_do_not_start_heavy_jobs(self):
        result = classify(["docs/README.md"])
        self.assertFalse(any(result.values()))

    def test_unknown_path_and_empty_diff_are_conservative(self):
        self.assertTrue(all(classify(["new-system/file.dat"]).values()))
        self.assertTrue(all(classify([]).values()))

    def test_non_pr_events_always_run_full(self):
        for event in ("push", "schedule", "workflow_dispatch"):
            self.assertTrue(all(classify(["docs/README.md"], event).values()))

    def test_surface_changes_are_independent(self):
        for path, expected in [("app/src/main/Foo.kt", "android"), ("web/app/page.tsx", "web"), ("site/app/page.tsx", "site"), ("launcher/ui.js", "companion"), ("control-bridge/foo.py", "bridge")]:
            with self.subTest(path=path):
                r=classify([path]); self.assertTrue(r[expected])
                self.assertFalse(r["supply_chain"])

    def test_shared_design_runs_all_consumers(self):
        r=classify(["design/icons/brand.svg"])
        for key in ("android", "instrumentation", "web", "site", "companion", "physical"):
            self.assertTrue(r[key], key)

    def test_api_and_auth_contracts_run_protocol_consumers(self):
        r=classify(["docs/FEDERATED_AUTH_V1.md"])
        for key in ("core", "postgres", "android", "web", "companion", "physical"):
            self.assertTrue(r[key], key)

    def test_build_release_and_workflows_run_everything(self):
        for path in (".github/workflows/build.yml", "scripts/change_classification.py", "VERSION", "gradle/wrapper/gradle-wrapper.properties", "server/pyproject.toml", "docs/RELEASE_GATES.md"):
            self.assertTrue(all(classify([path]).values()), path)

    def test_python_and_js_codeql_route_separately(self):
        r=classify(["server/app/core/foo.py"])
        self.assertTrue(r["codeql_python"]); self.assertFalse(r["codeql_javascript"])
        r=classify(["web/app/page.tsx"])
        self.assertTrue(r["codeql_javascript"]); self.assertFalse(r["codeql_python"])

    def test_deleted_or_renamed_old_path_remains_relevant(self):
        self.assertTrue(classify(["app/old.kt", "docs/new.txt"])["android"])

    def test_server_wire_contracts_select_every_consumer(self):
        for path in ('server/app/main.py', 'server/app/entrypoint.py', 'server/app/core/companion_websocket.py', 'server/app/core/recommendation_delivery.py', 'server/app/core/models.py', 'server/app/data/game-capability-catalog.v1.json'):
            result=classify([path])
            for key in ('android','instrumentation','web','companion','bridge'):
                self.assertTrue(result[key], (path,key))


class ExactGitDiffTests(unittest.TestCase):
    def test_nul_safe_deleted_renamed_and_newline_paths(self):
        import tempfile, subprocess, os
        from pathlib import Path
        from change_classification import event_paths
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def git(*args): return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('config','user.name','fixture'); git('config','user.email','fixture@example.invalid')
            (root/'app').mkdir(); (root/'app/removed.kt').write_text('old')
            git('add','.'); git('commit','-m','base'); base=git('rev-parse','HEAD')
            (root/'docs').mkdir(); (root/'app/removed.kt').rename(root/'docs/renamed.txt'); (root/'docs/new\nline.txt').write_text('new')
            git('add','.'); git('commit','-m','head'); head=git('rev-parse','HEAD')
            previous=os.getcwd()
            try:
                os.chdir(directory)
                paths=event_paths({'pull_request':{'base':{'sha':base},'head':{'sha':head}}})
                self.assertEqual(set(paths), {'app/removed.kt','docs/renamed.txt','docs/new\nline.txt'})
                self.assertTrue(classify(paths)['android'])
                with self.assertRaisesRegex(ValueError,'HEAD_MISMATCH'):
                    event_paths({'pull_request':{'base':{'sha':base},'head':{'sha':base}}})
                with self.assertRaisesRegex(ValueError,'INVALID_DIFF_SHA'):
                    event_paths({'pull_request':{'base':{'sha':'main;anything'},'head':{'sha':head}}})
            finally: os.chdir(previous)

if __name__ == "__main__": unittest.main()
