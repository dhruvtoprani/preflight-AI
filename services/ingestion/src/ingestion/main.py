from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from preflight_schemas import SourceDocument

from .connectors import SeedDumpConnector
from .sync import LiveSyncResult, sync_live_sources


@dataclass
class IngestionResult:
    documents_ingested: int
    output_path: str


def _default_output_path() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "index" / "seed_documents.jsonl"


def ingest_seed_documents(
    source_dir: Path | None = None,
    output_path: Path | None = None,
) -> IngestionResult:
    """Normalize exported docs to JSONL index for retrieval."""
    repo_root = Path(__file__).resolve().parents[4]
    active_source_dir = source_dir or repo_root / "data" / "seed_exports"
    active_output_path = output_path or _default_output_path()

    connector = SeedDumpConnector(active_source_dir)
    result = connector.fetch_updates()
    documents = result.documents

    active_output_path.parent.mkdir(parents=True, exist_ok=True)
    with active_output_path.open("w", encoding="utf-8") as file_obj:
        for document in documents:
            file_obj.write(document.model_dump_json())
            file_obj.write("\n")

    return IngestionResult(
        documents_ingested=len(documents),
        output_path=str(active_output_path),
    )


def sync_live_documents() -> LiveSyncResult:
    """Run live connector sync (Jira/Confluence) into normalized index."""
    return sync_live_sources()
