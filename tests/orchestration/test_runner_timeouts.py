from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.runners import DeterministicRunner
from preflight_schemas import InitiativeBrief


class RunnerTimeoutTests(unittest.TestCase):
    def test_runner_returns_partial_results_when_team_times_out(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        result = DeterministicRunner(timeout_teams=["qa"]).run(brief)

        self.assertEqual(len(result.team_reviews), 2)
        self.assertEqual([review.team for review in result.team_reviews], ["engineering", "support"])
        self.assertEqual(
            result.warnings,
            ["qa agent timed out; review contains partial results"],
        )


if __name__ == "__main__":
    unittest.main()
