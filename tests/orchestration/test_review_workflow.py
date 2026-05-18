from __future__ import annotations

import time
import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from ingestion.sync import ConnectorSyncResult, LiveSyncResult
from orchestrator.main import review
from orchestrator.runners import LLMTeamRunner
from preflight_schemas import InitiativeBrief


def _brief() -> InitiativeBrief:
    return InitiativeBrief(
        title="Automated pet health alerts",
        problem_statement="Users miss early warning signals for potential pet health changes.",
        proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
        target_timeline="Q3",
        affected_teams=["engineering", "qa"],
        success_metric="Reduce time-to-notice by 30%",
        known_constraints=["Telemetry schema freeze in August"],
    )


class SlowLLMClient:
    def complete(self, system_prompt: str, user_prompt: str):
        time.sleep(0.05)

        class _Response:
            content = (
                '{"readiness":"yellow","concerns":[{"statement":"Owner map is incomplete for kickoff.",' 
                '"confidence":0.6,"evidence_status":"inferred","blockers":["Assign owner"],' 
                '"questions":["Who owns API delivery?"],"evidence":[]}]}'
            )

        return _Response()


class WorkflowTests(unittest.TestCase):
    def test_llm_runner_applies_timeout_fallback(self) -> None:
        runner = LLMTeamRunner(
            llm_client=SlowLLMClient(),
            review_timeout_seconds=0.01,
            max_workers=2,
        )

        result = runner.run(_brief())

        self.assertEqual(len(result.team_reviews), 2)
        self.assertTrue(any("timed out" in warning for warning in result.warnings))

    def test_review_includes_sync_warnings_when_sync_before_review(self) -> None:
        sync_result = LiveSyncResult(
            documents_written=0,
            output_path="/tmp/index.jsonl",
            checkpoint_path="/tmp/checkpoints.json",
            connector_results=[
                ConnectorSyncResult(
                    connector="jira",
                    fetched_documents=0,
                    checkpoint_after=None,
                )
            ],
            warnings=["jira sync failed: timeout"],
        )

        with patch("orchestrator.main.sync_live_documents", return_value=sync_result):
            run = review(_brief(), sync_before_review=True)

        self.assertIn("jira sync failed: timeout", run.moderator_summary.warnings)


if __name__ == "__main__":
    unittest.main()
