from __future__ import annotations

import unittest

from pydantic import ValidationError

import tests.bootstrap  # noqa: F401
from preflight_schemas import Concern
from tests.helpers import load_fixture


class ReviewContractTests(unittest.TestCase):
    def test_valid_concern_payload_parses(self) -> None:
        payload = load_fixture("concern_valid.json")
        concern = Concern.model_validate(payload)
        self.assertEqual(concern.evidence_status.value, "evidence-backed")
        self.assertEqual(len(concern.evidence), 1)

    def test_invalid_evidence_status_fails_validation(self) -> None:
        payload = load_fixture("concern_invalid_evidence_status.json")
        with self.assertRaises(ValidationError):
            Concern.model_validate(payload)

    def test_evidence_backed_requires_evidence_reference(self) -> None:
        payload = load_fixture("concern_evidence_backed_without_evidence.json")
        with self.assertRaises(ValidationError):
            Concern.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
