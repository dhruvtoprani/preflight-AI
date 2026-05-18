from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from orchestrator.main import get_review_run, list_review_runs, review, runs_dashboard
from preflight_schemas import InitiativeBrief, ReadinessStatus


def _brief(title: str, requester: str) -> InitiativeBrief:
    return InitiativeBrief(
        title=title,
        problem_statement="Users miss early warning signals for potential pet health changes.",
        proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
        target_timeline="Q3",
        affected_teams=["engineering", "qa", "support"],
        success_metric="Reduce time-to-notice by 30%",
        known_constraints=["Telemetry schema freeze in August"],
        requester=requester,
        channel_id="C123",
        thread_ts="1712345678.90123",
    )


class RunHistoryTests(unittest.TestCase):
    def test_review_persists_and_history_supports_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "PREFLIGHT_RUN_DIR": temp_dir,
                    "DATABASE_URL": "",
                },
                clear=False,
            ):
                yellow_run = review(_brief("Initiative A", "pm-1"), timeout_team=["qa"])
                red_run = review(_brief("Initiative B", "pm-2"))

                all_runs = list_review_runs(limit=10)
                self.assertEqual(all_runs.total, 2)
                self.assertEqual(all_runs.runs[0].run_id, red_run.run_id)
                self.assertEqual(all_runs.runs[1].run_id, yellow_run.run_id)

                yellow_only = list_review_runs(readiness=ReadinessStatus.YELLOW)
                self.assertEqual(yellow_only.total, 1)
                self.assertEqual(yellow_only.runs[0].run_id, yellow_run.run_id)

                requester_only = list_review_runs(requester="pm-1")
                self.assertEqual(requester_only.total, 1)
                self.assertEqual(requester_only.runs[0].run_id, yellow_run.run_id)

                team_only = list_review_runs(team="engineering")
                self.assertEqual(team_only.total, 2)

    def test_get_run_and_dashboard_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "PREFLIGHT_RUN_DIR": temp_dir,
                    "DATABASE_URL": "",
                },
                clear=False,
            ):
                yellow_run = review(_brief("Initiative C", "pm-3"), timeout_team=["qa"])
                review(_brief("Initiative D", "pm-4"))

                found = get_review_run(yellow_run.run_id, include_sensitive=True)
                self.assertEqual(found.run_id, yellow_run.run_id)
                self.assertEqual(found.requester, "pm-3")

                dashboard = runs_dashboard(recent_limit=5)
                self.assertEqual(dashboard.total_runs, 2)
                self.assertEqual(dashboard.readiness.yellow, 1)
                self.assertEqual(dashboard.readiness.red, 1)
                self.assertTrue(len(dashboard.top_blockers) >= 1)
                self.assertTrue(len(dashboard.recent_runs) >= 2)


if __name__ == "__main__":
    unittest.main()
