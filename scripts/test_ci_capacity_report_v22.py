#!/usr/bin/env python3
"""Credential-free contract tests for cross-repository Actions capacity reporting."""
import datetime as dt
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

MODULE = pathlib.Path(__file__).with_name("ci_capacity_report_v22.py")
spec = importlib.util.spec_from_file_location("ci_budget_tool", MODULE)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)

class BudgetReportTests(unittest.TestCase):
    def test_part_minute_rounds_up_per_job(self):
        j={"started_at":"2026-10-25T10:00:00Z","completed_at":"2026-10-25T10:01:05Z"}
        self.assertEqual(budget.rounded_job_minutes(j),2)
    def test_skips_incomplete_job_without_inventing_time(self):
        jobs=[{"name":"a","started_at":"2026-10-25T10:00:00Z","completed_at":None},
              {"name":"b","started_at":"2026-10-25T10:00:00Z","completed_at":"2026-10-25T10:00:30Z"}]
        self.assertEqual(budget.sum_jobs(jobs),(1,1,[("b",1)]))
    def test_single_run_report_is_not_monthly_invoice(self):
        s=budget.render([{"repo":"spenskoj90-sudo/alpha-0","name":"FAST","rounded_wall_minutes":9}])
        self.assertIn("NOT GitHub Billing",s)
        self.assertIn("A partial recent-run sample",s)
        self.assertIn("FAST",s)
    def test_collect_only_reads_actions_run_and_jobs_api(self):
        urls=[]
        def fake(url):
            urls.append(url)
            if url.endswith("status=completed"):
                return {"workflow_runs":[{"id":1234,"name":"FAST","event":"pull_request","head_branch":"x","conclusion":"success"}]}
            return {"total_count":1,"jobs":[{"name":"unit","started_at":"2026-10-25T10:00:00Z","completed_at":"2026-10-25T10:00:20Z"}]}
        with patch.object(budget,"api",side_effect=fake):
            runs=budget.collect("spenskoj90-sudo/alpha-0",10)
        self.assertEqual(runs[0]["rounded_wall_minutes"],1)
        self.assertEqual(len(urls),2)
        self.assertTrue(all("/actions/" in u for u in urls))
    def test_rejects_unaccounted_paginated_jobs(self):
        def fake(url):
            if url.endswith("status=completed"):
                return {"workflow_runs":[{"id":1234}]}
            return {"total_count":101,"jobs":[]}
        with patch.object(budget,"api",side_effect=fake):
            with self.assertRaisesRegex(RuntimeError,"pagination"):
                budget.collect("spenskoj90-sudo/alpha-0",10)

if __name__=="__main__":
    unittest.main(verbosity=2)
