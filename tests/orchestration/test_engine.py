from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.engine import run_preflight
from orchestrator.moderator import DeterministicModerator
from orchestrator.runners import RunnerResult
from preflight_schemas import (
    AgentReview,
    Concern,
    EvidenceReference,
    EvidenceStatus,
    InitiativeBrief,
    ModeratorSummary,
    ReadinessStatus,
)


class StaticRunner:
    def run(self, brief: InitiativeBrief) -> RunnerResult:
        eng_concern = Concern(
            team="engineering",
            statement="Backend contract owner is not assigned for the alert API.",
            confidence=0.7,
            evidence_status=EvidenceStatus.INFERRED,
            evidence=[
                EvidenceReference(
                    source_type="roadmap",
                    source_id="roadmap-q3",
                    excerpt="Alert API milestone has no explicit owner.",
                )
            ],
            blockers=["Assign API owner"],
            questions=["Who is accountable for API rollout sequencing?"],
        )
        qa_concern = Concern(
            team="qa",
            statement="Regression coverage is incomplete for notification preference flows.",
            confidence=0.81,
            evidence_status=EvidenceStatus.EVIDENCE_BACKED,
            evidence=[
                EvidenceReference(
                    source_type="release_notes",
                    source_id="rn-q2",
                    excerpt="Prior releases had notification preference regressions.",
                )
            ],
            blockers=["Estimate test matrix"],
            questions=["What is the minimum beta coverage plan?"],
        )

        return RunnerResult(
            team_reviews=[
                AgentReview(
                    team="engineering",
                    readiness=ReadinessStatus.YELLOW,
                    concerns=[eng_concern],
                ),
                AgentReview(
                    team="qa", readiness=ReadinessStatus.RED, concerns=[qa_concern]
                ),
            ],
            warnings=["qa agent timed out; review contains partial results"],
        )


class StubModerator:
    def summarize(
        self,
        brief: InitiativeBrief,
        team_reviews: list[AgentReview],
        warnings: list[str] | None = None,
    ) -> ModeratorSummary:
        return ModeratorSummary(
            overall_readiness=ReadinessStatus.GREEN,
            blockers=["Custom blocker"],
            dependencies=["API schema sign-off"],
            questions_to_resolve=["Is beta cohort defined?"],
            suggested_owners=["TPM"],
            kickoff_agenda=["Align scope", "Set ownership"],
            warnings=list(warnings or []),
        )


class EngineTests(unittest.TestCase):
    def test_run_preflight_uses_runner_and_aggregates_summary(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        result = run_preflight(
            brief,
            runner=StaticRunner(),
            moderator=DeterministicModerator(),
        )

        self.assertEqual(result.initiative_title, brief.title)
        self.assertEqual(result.moderator_summary.overall_readiness, ReadinessStatus.RED)
        self.assertIn("Assign API owner", result.moderator_summary.blockers)
        self.assertIn("Estimate test matrix", result.moderator_summary.blockers)
        self.assertIn(
            "Who is accountable for API rollout sequencing?",
            result.moderator_summary.questions_to_resolve,
        )
        self.assertIn("QA Lead", result.moderator_summary.suggested_owners)
        self.assertIn(
            "qa agent timed out; review contains partial results",
            result.moderator_summary.warnings,
        )

    def test_run_preflight_supports_injected_moderator(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        result = run_preflight(
            brief,
            runner=StaticRunner(),
            moderator=StubModerator(),
        )

        self.assertEqual(result.moderator_summary.overall_readiness, ReadinessStatus.GREEN)
        self.assertEqual(result.moderator_summary.blockers, ["Custom blocker"])
        self.assertEqual(result.moderator_summary.dependencies, ["API schema sign-off"])
        self.assertIn(
            "qa agent timed out; review contains partial results",
            result.moderator_summary.warnings,
        )


if __name__ == "__main__":
    unittest.main()
