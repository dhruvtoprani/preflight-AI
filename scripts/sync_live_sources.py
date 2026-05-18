#!/usr/bin/env python3
from __future__ import annotations

import json

from ingestion.main import sync_live_documents


def main() -> None:
    result = sync_live_documents()
    print(
        json.dumps(
            {
                "documents_written": result.documents_written,
                "output_path": result.output_path,
                "checkpoint_path": result.checkpoint_path,
                "connector_results": [
                    {
                        "connector": item.connector,
                        "fetched_documents": item.fetched_documents,
                        "checkpoint_after": item.checkpoint_after,
                    }
                    for item in result.connector_results
                ],
                "warnings": result.warnings,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
