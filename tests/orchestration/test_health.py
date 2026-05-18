from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from orchestrator.health import build_full_health_payload


class HealthTests(unittest.TestCase):
    def test_health_payload_reports_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_file = Path(temp_dir) / "policy.json"
            policy_file.write_text("{}", encoding="utf-8")
            template_dir = Path(temp_dir) / "templates"
            template_dir.mkdir(parents=True, exist_ok=True)
            index_file = Path(temp_dir) / "index.jsonl"
            index_file.write_text("", encoding="utf-8")

            env = {
                "PREFLIGHT_TEAM_POLICY_PATH": str(policy_file),
                "PREFLIGHT_PROMPT_TEMPLATE_DIR": str(template_dir),
                "PREFLIGHT_INDEX_PATH": str(index_file),
                "PREFLIGHT_RUNNER_MODE": "auto",
                "PREFLIGHT_RUN_DIR": str(Path(temp_dir) / "runs"),
                "DATABASE_URL": "",
            }

            with patch.dict(os.environ, env, clear=False):
                payload = build_full_health_payload()

            self.assertIn("status", payload)
            self.assertIn("checks", payload)
            self.assertIn("jira_connector_config", payload["checks"])
            self.assertIn("confluence_connector_config", payload["checks"])
            self.assertIn("persistence", payload["checks"])
            self.assertIn("persistence", payload)
            self.assertIn("run_dir", payload["paths"])


if __name__ == "__main__":
    unittest.main()
