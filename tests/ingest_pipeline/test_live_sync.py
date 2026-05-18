from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from ingestion.checkpoints import CheckpointStore
from ingestion.connectors import ConnectorFetchResult
from ingestion.sync import sync_live_sources
from preflight_schemas import SourceDocument


class FakeConnector:
    def __init__(self, name: str, documents: list[SourceDocument], cursor: str) -> None:
        self.name = name
        self.documents = documents
        self.cursor = cursor
        self.received_since: str | None = None

    def fetch_updates(self, since_cursor: str | None = None) -> ConnectorFetchResult:
        self.received_since = since_cursor
        return ConnectorFetchResult(documents=self.documents, next_cursor=self.cursor)


class LiveSyncTests(unittest.TestCase):
    def test_sync_live_sources_merges_and_checkpoints(self) -> None:
        doc_v1 = SourceDocument(
            source_id="JIRA-1",
            source_type="jira",
            title="Initial title",
            body="initial body",
            team_scope=["engineering"],
            tags=["team:engineering"],
        )
        doc_v2 = SourceDocument(
            source_id="JIRA-1",
            source_type="jira",
            title="Updated title",
            body="updated body",
            team_scope=["engineering"],
            tags=["team:engineering"],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.jsonl"
            checkpoint_path = Path(temp_dir) / "checkpoints.json"

            first_connector = FakeConnector("jira", [doc_v1], "2026-05-18T10:00:00.000+0000")
            first_result = sync_live_sources(
                connectors=[first_connector],
                output_path=index_path,
                checkpoint_store=CheckpointStore(path=checkpoint_path),
            )

            second_connector = FakeConnector("jira", [doc_v2], "2026-05-18T11:00:00.000+0000")
            second_result = sync_live_sources(
                connectors=[second_connector],
                output_path=index_path,
                checkpoint_store=CheckpointStore(path=checkpoint_path),
            )

            self.assertEqual(first_result.documents_written, 1)
            self.assertEqual(second_result.documents_written, 1)
            self.assertEqual(second_connector.received_since, "2026-05-18T10:00:00.000+0000")

            lines = index_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            stored = SourceDocument.model_validate(json.loads(lines[0]))
            self.assertEqual(stored.title, "Updated title")

            checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_payload["jira"], "2026-05-18T11:00:00.000+0000")


if __name__ == "__main__":
    unittest.main()
