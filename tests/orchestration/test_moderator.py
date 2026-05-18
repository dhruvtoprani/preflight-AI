from __future__ import annotations

import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from orchestrator.moderator import (
    DeterministicModerator,
    LLMModerator,
    ModeratorConfig,
    build_default_moderator,
)
from preflight_schemas import (
    AgentReview,
    Concern,
    EvidenceReference,
    EvidenceStatus,
    InitiativeBrief,
    ReadinessStatus,
)


class _Response:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLMClientSuccess:
    def complete(self, system_prompt: str, user_prompt: str) -> _Response:
        return _Response(
            '{'
            '"overall_readiness":"red",'
            '"blockers":["B1","B1","B2","B3"],'
            '"dependencies":["D1","D2"],'
            '"questions_to_resolve":["Q1","Q2","Q3"],'
            '"suggested_owners":["Owner1","Owner1","Owner2"],'
            '"kickoff_agenda":["A1","A2","A3"]'
            '}'
        )


class FakeLLMClientInvalidJson:
    def complete(self, system_prompt: str, user_prompt: str) -> _Response:
        return _Response("not-json")


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


def _team_reviews() -> list[AgentReview]:
    eng_concern = Concern(
        team="engineering",
        statement="API ownership is not explicit for rollout sequencing.",
        confidence=0.72,
        evidence_status=EvidenceStatus.INFERRED,
        evidence=[],
        blockers=["Assign API owner"],
        questions=["Who owns API contract?"],
    )
    qa_concern = Concern(
        team="qa",
        statement="Regression risk exists across notification and onboarding paths.",
        confidence=0.84,
        evidence_status=EvidenceStatus.EVIDENCE_BACKED,
        evidence=[
            EvidenceReference(
                source_type="release_notes",
                source_id="q2-release",
                excerpt="Prior release had onboarding notification regressions.",
            )
        ],
        blockers=["Estimate test matrix"],
        questions=["What is minimum beta test coverage?"],
    )

    return [
        AgentReview(team="engineering", readiness=ReadinessStatus.YELLOW, concerns=[eng_concern]),
        AgentReview(team="qa", readiness=ReadinessStatus.RED, concerns=[qa_concern]),
    ]


class ModeratorTests(unittest.TestCase):
    def test_llm_moderator_uses_payload_and_applies_limits(self) -> None:
        moderator = LLMModerator(
            llm_client=FakeLLMClientSuccess(),
            config=ModeratorConfig(
                max_blockers=2,
                max_dependencies=1,
                max_questions=2,
                max_owners=1,
                max_agenda_items=2,
            ),
        )

        summary = moderator.summarize(
            brief=_brief(),
            team_reviews=_team_reviews(),
            warnings=["runner warning"],
        )

        self.assertEqual(summary.overall_readiness, ReadinessStatus.RED)
        self.assertEqual(summary.blockers, ["B1", "B2"])
        self.assertEqual(summary.dependencies, ["D1"])
        self.assertEqual(summary.questions_to_resolve, ["Q1", "Q2"])
        self.assertEqual(summary.suggested_owners, ["Owner1"])
        self.assertEqual(summary.kickoff_agenda, ["A1", "A2"])
        self.assertIn("runner warning", summary.warnings)

    def test_llm_moderator_falls_back_to_deterministic_on_invalid_json(self) -> None:
        moderator = LLMModerator(
            llm_client=FakeLLMClientInvalidJson(),
            config=ModeratorConfig(),
        )

        summary = moderator.summarize(
            brief=_brief(),
            team_reviews=_team_reviews(),
            warnings=["existing warning"],
        )

        self.assertEqual(summary.overall_readiness, ReadinessStatus.RED)
        self.assertIn("Assign API owner", summary.blockers)
        self.assertIn("Estimate test matrix", summary.blockers)
        self.assertTrue(
            any("moderator synthesis fallback used" in warning for warning in summary.warnings)
        )
        self.assertIn("existing warning", summary.warnings)

    def test_build_default_moderator_uses_deterministic_when_llm_unavailable(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PREFLIGHT_MODERATOR_MODE": "llm",
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            moderator = build_default_moderator()

        self.assertIsInstance(moderator, DeterministicModerator)


if __name__ == "__main__":
    unittest.main()
