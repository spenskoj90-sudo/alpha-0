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
        for path in ("server/Dockerfile", "Dockerfile", "server/Dockerfile.staging", ".github/workflows/build.yml", "scripts/change_classification.py", "VERSION", "gradle/wrapper/gradle-wrapper.properties", "docs/RELEASE_GATES.md"):
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

    def test_known_node_dependency_metadata_preserves_security_without_unrelated_hosts(self):
        for surface, flag in [('web', 'web'), ('site', 'site'), ('launcher', 'companion')]:
            for file in ('package.json', 'package-lock.json'):
                result = classify([f'{surface}/{file}'])
                for key in (flag, 'dependencies', 'audit_javascript', 'codeql_javascript', 'supply_chain', 'p1', 'release'):
                    self.assertTrue(result[key], (surface, file, key))
                for key in ('android', 'instrumentation', 'physical', 'postgres', 'core', 'bridge'):
                    self.assertFalse(result[key], (surface, file, key))
                for other in ('web', 'site', 'companion'):
                    if other != flag: self.assertFalse(result[other], (surface, other))

    def test_core_dependencies_retain_wire_consumers_but_not_unrelated_public_site(self):
        result = classify(['server/pyproject.toml'])
        for key in ('core', 'postgres', 'android', 'instrumentation', 'web', 'companion', 'bridge', 'p1', 'container', 'supply_chain', 'dependencies', 'audit_python', 'codeql_python'):
            self.assertTrue(result[key], key)
        self.assertFalse(result['site'])

    def test_shared_unknown_and_mixed_metadata_fail_closed(self):
        for path in ('package.json', 'new-service/package-lock.json', 'server/nested/pyproject.toml', 'app/build.gradle.kts'):
            self.assertTrue(all(classify([path]).values()), path)
        result = classify(['web/package-lock.json', 'site/package.json'])
        self.assertTrue(result['web']); self.assertTrue(result['site'])
        self.assertFalse(result['android'])


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
