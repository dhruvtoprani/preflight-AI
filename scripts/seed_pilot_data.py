from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATHS = [
    ROOT / "packages/schemas/src",
    ROOT / "packages/shared-utils/src",
    ROOT / "services/ingestion/src",
]

for src_path in reversed(SRC_PATHS):
    src_string = str(src_path)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)

from ingestion.main import ingest_seed_documents  # noqa: E402


if __name__ == "__main__":
    result = ingest_seed_documents()
    print(
        json.dumps(
            {
                "documents_ingested": result.documents_ingested,
                "output_path": result.output_path,
            },
            indent=2,
            sort_keys=True,
        )
    )
