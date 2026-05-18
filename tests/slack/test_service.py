from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from preflight_schemas import InitiativeBrief, ReviewRun
from slack_bot.idempotency import IdempotencyStore
from slack_bot.persistence import ReviewRunStore
from slack_bot.service import process_brief


class _StubMessenger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def post_message(self, channel: str, text: str, thread_ts: str | None = None):
        self.messages.append(text)


class ServiceTests(unittest.TestCase):
    def test_process_brief_handles_duplicate(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
            requester="U123",
            channel_id="C123",
            thread_ts="1710000000.000100",
        )

        def fake_review_runner(b: InitiativeBrief) -> ReviewRun:
            from orchestrator.main import review

            return review(b, timeout_team=["qa"])

        with tempfile.TemporaryDirectory() as temp_dir:
            run_store = ReviewRunStore(run_dir=Path(temp_dir) / "runs")
            idem_store = IdempotencyStore(path=Path(temp_dir) / "idem.json")

            first = process_brief(brief, fake_review_runner, run_store, idem_store)
            second = process_brief(brief, fake_review_runner, run_store, idem_store)

            self.assertFalse(first.duplicate)
            self.assertTrue(second.duplicate)


if __name__ == "__main__":
    unittest.main()
