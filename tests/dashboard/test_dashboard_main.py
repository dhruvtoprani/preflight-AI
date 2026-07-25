from __future__ import annotations

import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from dashboard_app.main import (
    api_dashboard,
    api_demo,
    api_run_detail,
    demo,
    history,
    index,
    run_detail,
)


class DashboardTests(unittest.TestCase):
    def test_api_dashboard_aggregates_contract_responses(self) -> None:
        captured: list[tuple[str, dict[str, str] | None]] = []

        def fake_fetch(path: str, query: dict[str, str] | None = None) -> dict:
            captured.append((path, query))
            if path == "/runs/dashboard":
                return {
                    "total_runs": 2,
                    "readiness": {"green": 0, "yellow": 1, "red": 1},
                    "top_blockers": ["Assign API owner"],
                    "recent_runs": [],
                }
            if path == "/runs":
                return {"total": 2, "runs": []}
            raise AssertionError(f"unexpected path: {path}")

        with patch("dashboard_app.main._fetch_json", side_effect=fake_fetch):
            result = api_dashboard(
                recent_limit=7,
                list_limit=15,
                readiness="yellow",
                team="engineering",
                requester="pm-1",
                initiative_contains="alerts",
            )

        self.assertEqual(result["dashboard"]["total_runs"], 2)
        self.assertEqual(result["runs"]["total"], 2)
        self.assertEqual(captured[0][0], "/runs/dashboard")
        self.assertEqual(captured[0][1]["recent_limit"], "7")
        self.assertEqual(captured[0][1]["team"], "engineering")
        self.assertEqual(captured[1][0], "/runs")
        self.assertEqual(captured[1][1]["limit"], "15")
        self.assertEqual(captured[1][1]["readiness"], "yellow")

    def test_api_run_detail_passthrough(self) -> None:
        with patch("dashboard_app.main._fetch_json", return_value={"run_id": "abc"}) as mocked:
            result = api_run_detail("abc")

        self.assertEqual(result["run_id"], "abc")
        mocked.assert_called_once_with("/runs/abc")

    def test_history_renders_dashboard_shell(self) -> None:
        html = history()
        self.assertIn("PreFlight Run Dashboard", html)
        self.assertIn("/api/dashboard", html)
        self.assertIn("initiative_contains", html)

    def test_index_renders_slack_demo(self) -> None:
        html = index()
        self.assertIn("# preflight-demo", html)
        self.assertIn("/api/demo", html)
        self.assertNotIn('href="/">Dashboard</a>', html)

    def test_demo_api_returns_offline_scenarios(self) -> None:
        payload = api_demo()

        self.assertGreaterEqual(payload["scenario_count"], 3)
        self.assertGreaterEqual(payload["evidence_backed_ratio"], 0.3)
        self.assertIn("slack_message", payload["scenarios"][0])
        self.assertIn("run", payload["scenarios"][0])

    def test_demo_renders_slack_channel_shell(self) -> None:
        html = demo()
        self.assertIn("# preflight-demo", html)
        self.assertIn("/api/demo", html)
        self.assertIn("Kickoff risks, in a Slack thread.", html)
        self.assertIn("What are we preflighting?", html)
        self.assertIn("Health alerts launch", html)
        self.assertIn("Parsed brief and selected", html)
        self.assertIn("Opening #preflight-demo", html)
        self.assertIn("Syncing source graph", html)
        self.assertIn("Source triage", html)

    def test_run_detail_renders_shell(self) -> None:
        html = run_detail("run-123")
        self.assertIn("Back to demo", html)
        self.assertIn("/api/runs/", html)
        self.assertIn("run-123", html)


if __name__ == "__main__":
    unittest.main()
