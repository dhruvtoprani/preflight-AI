from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from ingestion.main import ingest_seed_documents


class SeedIngestionTests(unittest.TestCase):
    def test_ingests_seed_docs_to_jsonl_index(self) -> None:
        fixture_source = (
            Path(__file__).resolve().parents[1] / "fixtures" / "seed_exports"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "seed_documents.jsonl"
            result = ingest_seed_documents(
                source_dir=fixture_source,
                output_path=output_path,
            )

            self.assertEqual(result.documents_ingested, 3)
            self.assertEqual(result.output_path, str(output_path))
            self.assertTrue(output_path.exists())
            self.assertEqual(len(output_path.read_text(encoding="utf-8").splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
