from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATHS = [
    ROOT / "packages/schemas/src",
    ROOT / "packages/shared-utils/src",
    ROOT / "services/orchestrator/src",
    ROOT / "services/ingestion/src",
    ROOT / "services/retrieval/src",
    ROOT / "apps/slack-bot/src",
    ROOT / "apps/dashboard/src",
]

for src_path in reversed(SRC_PATHS):
    src_string = str(src_path)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)

# Keep tests deterministic even when local shell exports production credentials.
os.environ.setdefault("PREFLIGHT_RUNNER_MODE", "deterministic")
os.environ.setdefault("PREFLIGHT_MODERATOR_MODE", "deterministic")
os.environ.setdefault("DATABASE_URL", "")
