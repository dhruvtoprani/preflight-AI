from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.runners import LLMTeamRunner
from preflight_schemas import InitiativeBrief


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str):
        self.calls.append((system_prompt, user_prompt))

        class _Response:
            content = (
                '{"readiness":"yellow","concerns":[{"statement":"Need clearer owner map for API contract.",' 
                '"confidence":0.71,"evidence_status":"inferred","blockers":["Assign API owner"],' 
                '"questions":["Who owns API contract?"],"evidence":[]}]}'
            )

        return _Response()


class LLMRunnerTests(unittest.TestCase):
    def test_llm_runner_generates_team_reviews_and_uses_policy_prompting(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        fake_client = FakeLLMClient()
        runner = LLMTeamRunner(llm_client=fake_client)
        result = runner.run(brief)

        self.assertEqual(len(result.team_reviews), 2)
        self.assertEqual(len(fake_client.calls), 2)
        second_prompt = fake_client.calls[0][1]
        self.assertIn("ALLOWED DOCUMENTATION SOURCES", second_prompt)
        self.assertIn("TEAM-SCOPED CONTEXT SNIPPETS", second_prompt)


if __name__ == "__main__":
    unittest.main()
