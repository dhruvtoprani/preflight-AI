from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from preflight_schemas import SourceDocument

from .checkpoints import CheckpointStore
from .connectors import (
    ConfluenceConnector,
    JiraConnector,
    SourceConnector,
)


@dataclass
class ConnectorSyncResult:
    connector: str
    fetched_documents: int
    checkpoint_after: str | None


@dataclass
class LiveSyncResult:
    documents_written: int
    output_path: str
    checkpoint_path: str
    connector_results: list[ConnectorSyncResult]
    warnings: list[str]


def _default_index_path() -> Path:
    return Path(tempfile.gettempdir()) / "preflight-ai" / "seed_documents.jsonl"


def _load_existing_documents(index_path: Path) -> dict[str, SourceDocument]:
    if not index_path.exists():
        return {}

    by_key: dict[str, SourceDocument] = {}
    with index_path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            raw = line.strip()
            if not raw:
                continue
            doc = SourceDocument.model_validate(json.loads(raw))
            key = f"{doc.source_type}::{doc.source_id}"
            by_key[key] = doc
    return by_key


def _write_documents(index_path: Path, documents: dict[str, SourceDocument]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as file_obj:
        for key in sorted(documents.keys()):
            file_obj.write(documents[key].model_dump_json())
            file_obj.write("\n")


def load_default_live_connectors() -> list[SourceConnector]:
    connectors: list[SourceConnector] = []
    jira = JiraConnector.from_env()
    if jira is not None:
        connectors.append(jira)

    confluence = ConfluenceConnector.from_env()
    if confluence is not None:
        connectors.append(confluence)

    return connectors


def sync_live_sources(
    connectors: list[SourceConnector] | None = None,
    output_path: Path | None = None,
    checkpoint_store: CheckpointStore | None = None,
) -> LiveSyncResult:
    active_connectors = connectors if connectors is not None else load_default_live_connectors()
    active_output_path = output_path or Path(os.getenv("PREFLIGHT_INDEX_PATH", _default_index_path()))
    active_checkpoint_store = checkpoint_store or CheckpointStore()
    active_checkpoint_store.load()

    documents_by_key = _load_existing_documents(active_output_path)
    warnings: list[str] = []
    connector_results: list[ConnectorSyncResult] = []

    for connector in active_connectors:
        connector_name = getattr(connector, "name", connector.__class__.__name__.lower())
        since_cursor = active_checkpoint_store.get(connector_name)

        try:
            fetch_result = connector.fetch_updates(since_cursor=since_cursor)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{connector_name} sync failed: {exc}")
            connector_results.append(
                ConnectorSyncResult(
                    connector=connector_name,
                    fetched_documents=0,
                    checkpoint_after=since_cursor,
                )
            )
            continue

        for document in fetch_result.documents:
            key = f"{document.source_type}::{document.source_id}"
            documents_by_key[key] = document

        active_checkpoint_store.set(connector_name, fetch_result.next_cursor)
        connector_results.append(
            ConnectorSyncResult(
                connector=connector_name,
                fetched_documents=len(fetch_result.documents),
                checkpoint_after=fetch_result.next_cursor,
            )
        )

    _write_documents(active_output_path, documents_by_key)
    active_checkpoint_store.save()

    return LiveSyncResult(
        documents_written=len(documents_by_key),
        output_path=str(active_output_path),
        checkpoint_path=str(active_checkpoint_store.path),
        connector_results=connector_results,
        warnings=warnings,
    )
