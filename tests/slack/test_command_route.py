from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from preflight_schemas import InitiativeBrief
from slack_bot.main import SlackRequestBody, call_orchestrator_review, slack_command


class CommandRouteTests(unittest.TestCase):
    def test_orchestrator_query_includes_sync_flag(self) -> None:
        brief = InitiativeBrief(
            title="Automated pet health alerts",
            problem_statement="Users miss early warning signals for potential pet health changes.",
            proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
            target_timeline="Q3",
            affected_teams=["engineering", "qa", "support"],
            success_metric="Reduce time-to-notice by 30%",
            known_constraints=["Telemetry schema freeze in August"],
        )

        captured_urls: list[str] = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                from orchestrator.main import review

                run = review(brief)
                return run.model_dump_json().encode("utf-8")

        def fake_urlopen(request, timeout=30):
            captured_urls.append(request.full_url)
            return FakeResponse()

        with patch.dict(os.environ, {"PREFLIGHT_SYNC_BEFORE_REVIEW": "true"}, clear=False):
            with patch("slack_bot.main.urlopen", side_effect=fake_urlopen):
                _ = call_orchestrator_review(brief)

        self.assertTrue(captured_urls)
        self.assertIn("sync_before_review=true", captured_urls[0])

    def test_slack_command_accepts_and_queues_structured_request(self) -> None:
        payload = SlackRequestBody(
            channel_id="C123",
            user_id="U123",
            text=(
                "title: Automated pet health alerts\n"
                "problem: Users miss early warning signals for potential pet health changes.\n"
                "solution: Generate proactive mobile alerts from telemetry trend changes.\n"
                "timeline: Q3\n"
                "teams: engineering, qa, tpm\n"
                "metric: Reduce time-to-notice by 30%\n"
                "constraints: Telemetry schema freeze in August"
            ),
            thread_ts="1710000000.000100",
        )

        with patch.dict(os.environ, {"PREFLIGHT_SLACK_ASYNC": "true"}, clear=False):
            with patch("slack_bot.main._execute_slack_review", return_value=None):
                response = slack_command(payload)

        self.assertEqual(response.status, "accepted")

    def test_slack_command_returns_team_guidance_for_invalid_teams(self) -> None:
        payload = SlackRequestBody(
            channel_id="C123",
            user_id="U123",
            text=(
                "title: Automated pet health alerts\n"
                "problem: Users miss early warning signals for potential pet health changes.\n"
                "solution: Generate proactive mobile alerts from telemetry trend changes.\n"
                "timeline: Q3\n"
                "teams: engineering/qa\n"
                "metric: Reduce time-to-notice by 30%\n"
                "constraints: Telemetry schema freeze in August"
            ),
            thread_ts="1710000000.000100",
        )

        response = slack_command(payload)
        self.assertEqual(response.status, "needs_input")
        self.assertIn("Canonical teams:", response.message)
        self.assertIn("Alias mapping:", response.message)

    def test_slack_command_requests_missing_fields_when_unstructured(self) -> None:
        payload = SlackRequestBody(
            channel_id="C123",
            user_id="U123",
            text="please review this kickoff idea",
            thread_ts="1710000000.000100",
        )

        response = slack_command(payload)
        self.assertEqual(response.status, "needs_input")
        self.assertIn("Please send the initiative in this format", response.message)


if __name__ == "__main__":
    unittest.main()
