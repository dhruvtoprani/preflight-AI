from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from ingestion.main import ingest_seed_documents
from retrieval.main import retrieve_context


class RetrievalTests(unittest.TestCase):
    def test_retrieval_respects_team_scope(self) -> None:
        fixture_source = (
            Path(__file__).resolve().parents[1] / "fixtures" / "seed_exports"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "seed_documents.jsonl"
            ingest_seed_documents(source_dir=fixture_source, output_path=index_path)

            qa_results = retrieve_context(
                team="qa",
                query="notification regression checklist",
                index_path=index_path,
            )
            eng_results_same_query = retrieve_context(
                team="engineering",
                query="notification regression checklist",
                index_path=index_path,
            )
            eng_results_global_query = retrieve_context(
                team="engineering",
                query="launch beta milestones",
                index_path=index_path,
            )

            qa_source_ids = {result.source_id for result in qa_results}
            eng_same_query_ids = {result.source_id for result in eng_results_same_query}
            eng_global_query_ids = {result.source_id for result in eng_results_global_query}

            self.assertIn("CONF-77", qa_source_ids)
            self.assertNotIn("CONF-77", eng_same_query_ids)
            self.assertIn("ROADMAP-Q3", eng_global_query_ids)


if __name__ == "__main__":
    unittest.main()
