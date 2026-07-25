from __future__ import annotations

import json
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from preflight_schemas import InitiativeBrief

ROOT = Path(__file__).resolve().parents[2]
DEMO_BRIEF_DIR = ROOT / "docs" / "pilot" / "demo_briefs"


class DemoBriefTests(unittest.TestCase):
    def test_demo_briefs_validate_against_initiative_schema(self) -> None:
        paths = sorted(DEMO_BRIEF_DIR.glob("*.json"))
        self.assertGreaterEqual(len(paths), 3)

        for path in paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                brief = InitiativeBrief.model_validate(payload)
                self.assertEqual(brief.title, payload["title"])
                self.assertGreaterEqual(len(brief.affected_teams), 3)


if __name__ == "__main__":
    unittest.main()
