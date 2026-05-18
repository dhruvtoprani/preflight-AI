from __future__ import annotations

import unittest

from pydantic import ValidationError

import tests.bootstrap  # noqa: F401
from preflight_schemas import InitiativeBrief
from tests.helpers import load_fixture


class InitiativeContractTests(unittest.TestCase):
    def test_valid_initiative_payload_parses(self) -> None:
        payload = load_fixture("initiative_valid.json")
        model = InitiativeBrief.model_validate(payload)
        self.assertEqual(model.title, payload["title"])
        self.assertEqual(model.affected_teams, payload["affected_teams"])

    def test_missing_required_field_fails_validation(self) -> None:
        payload = load_fixture("initiative_missing_problem_statement.json")
        with self.assertRaises(ValidationError):
            InitiativeBrief.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
