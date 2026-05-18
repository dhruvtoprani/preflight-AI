from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from preflight_schemas import (
    AgentReview,
    Concern,
    EvidenceReference,
    EvidenceStatus,
    ModeratorSummary,
    ReadinessStatus,
    ReviewRun,
)
from slack_bot.formatter import format_thread_message


class FormatterTests(unittest.TestCase):
    def test_formatter_includes_warnings_and_team_sections(self) -> None:
        concern = Concern(
            team="qa",
            statement="Regression risk in notification migration path.",
            confidence=0.81,
            evidence_status=EvidenceStatus.EVIDENCE_BACKED,
            evidence=[
                EvidenceReference(
                    source_type="release_notes",
                    source_id="q2-release",
                    excerpt="Two regressions linked to notification settings migration.",
                )
            ],
            blockers=["Estimate test matrix"],
            questions=["What beta coverage do we need?"],
        )

        run = ReviewRun(
            run_id="run-123",
            initiative_title="Automated pet health alerts",
            team_reviews=[
                AgentReview(
                    team="qa", readiness=ReadinessStatus.RED, concerns=[concern]
                )
            ],
            moderator_summary=ModeratorSummary(
                overall_readiness=ReadinessStatus.RED,
                blockers=["Estimate test matrix"],
                questions_to_resolve=["What beta coverage do we need?"],
                suggested_owners=["QA Lead"],
                kickoff_agenda=["Resolve blockers"],
                warnings=["engineering agent timed out; review contains partial results"],
            ),
        )

        output = format_thread_message(run)
        self.assertIn("Overall readiness: RED", output)
        self.assertIn("Warnings:", output)
        self.assertIn("Team perspectives:", output)
        self.assertIn("QA: RED", output)


if __name__ == "__main__":
    unittest.main()
