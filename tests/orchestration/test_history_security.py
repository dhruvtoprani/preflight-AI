from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from fastapi import HTTPException
from orchestrator.main import get_review_run, list_review_runs, review
from preflight_schemas import InitiativeBrief


def _brief(title: str, requester: str) -> InitiativeBrief:
    return InitiativeBrief(
        title=title,
        problem_statement="Users miss early warning signals for potential pet health changes.",
        proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
        target_timeline="Q3",
        affected_teams=["engineering", "qa", "support"],
        success_metric="Reduce time-to-notice by 30%",
        known_constraints=["Telemetry schema freeze in August"],
        requester=requester,
        channel_id="C12345678",
        thread_ts="1712345678.90123",
    )


class RunHistorySecurityTests(unittest.TestCase):
    def test_history_auth_is_enforced_when_token_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "PREFLIGHT_RUN_DIR": temp_dir,
                    "DATABASE_URL": "",
                    "PREFLIGHT_HISTORY_API_TOKEN": "secret-token",
                },
                clear=False,
            ):
                review(_brief("Initiative Auth", "pm-auth"))

                with self.assertRaises(HTTPException) as missing_ctx:
                    list_review_runs(limit=5)
                self.assertEqual(missing_ctx.exception.status_code, 401)

                with self.assertRaises(HTTPException) as wrong_ctx:
                    list_review_runs(limit=5, authorization="Bearer wrong")
                self.assertEqual(wrong_ctx.exception.status_code, 403)

                ok = list_review_runs(limit=5, authorization="Bearer secret-token")
                self.assertGreaterEqual(ok.total, 1)

    def test_history_redaction_is_default_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "PREFLIGHT_RUN_DIR": temp_dir,
                    "DATABASE_URL": "",
                    "PREFLIGHT_HISTORY_API_TOKEN": "secret-token",
                },
                clear=False,
            ):
                created = review(_brief("Launch for jane@example.com", "pm-sensitive"))

                redacted_list = list_review_runs(
                    limit=5,
                    authorization="Bearer secret-token",
                )
                self.assertIsNone(redacted_list.runs[0].requester)
                self.assertIn("[redacted-email]", redacted_list.runs[0].initiative_title)

                redacted_detail = get_review_run(
                    created.run_id,
                    authorization="Bearer secret-token",
                )
                self.assertIsNone(redacted_detail.requester)
                self.assertIsNone(redacted_detail.channel_id)
                self.assertIsNone(redacted_detail.thread_ts)

                full_detail = get_review_run(
                    created.run_id,
                    include_sensitive=True,
                    authorization="Bearer secret-token",
                )
                self.assertEqual(full_detail.requester, "pm-sensitive")
                self.assertEqual(full_detail.channel_id, "C12345678")


if __name__ == "__main__":
    unittest.main()
