from __future__ import annotations

import unittest

import tests.bootstrap  # noqa: F401
from orchestrator.prompting import PromptRepository


class PromptTemplateTests(unittest.TestCase):
    def test_team_templates_exist_or_fallback(self) -> None:
        repo = PromptRepository()
        self.assertIn("Engineering lens", repo.load_team_template("engineering"))
        self.assertIn("QA lens", repo.load_team_template("qa"))
        self.assertIn("TPM lens", repo.load_team_template("tpm"))


if __name__ == "__main__":
    unittest.main()
