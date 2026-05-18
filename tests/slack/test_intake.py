from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.bootstrap  # noqa: F401

from orchestrator.main import review
from preflight_schemas import InitiativeBrief
from slack_bot.main import intake


class IntakeIntegrationTests(unittest.TestCase):
    def test_intake_calls_orchestrator_formats_and_persists(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        def fake_call_orchestrator_review(
            brief: InitiativeBrief,
            timeout_team: list[str] | None = None,
            sync_before_review: bool | None = None,
        ):
            return review(brief=brief, timeout_team=timeout_team)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"PREFLIGHT_RUN_DIR": temp_dir}, clear=False):
                with patch(
                    "slack_bot.main.call_orchestrator_review",
                    side_effect=fake_call_orchestrator_review,
                ):
                    result = intake(brief=brief, timeout_team=["qa"])

            self.assertEqual(result.persisted_in, "file")
            self.assertTrue(result.persisted_path is not None)
            self.assertTrue(Path(result.persisted_path).exists())
            self.assertIn("Overall readiness", result.thread_preview)
            self.assertIn("partial results", " ".join(result.warnings))


if __name__ == "__main__":
    unittest.main()
