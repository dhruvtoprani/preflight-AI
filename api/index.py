from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Add monorepo service/package source roots for runtime imports.
for rel_path in [
    "packages/schemas/src",
    "packages/shared-utils/src",
    "services/orchestrator/src",
    "services/ingestion/src",
    "services/retrieval/src",
    "apps/slack-bot/src",
    "apps/dashboard/src",
]:
    abs_path = ROOT / rel_path
    if abs_path.exists():
        sys.path.insert(0, str(abs_path))

from dashboard_app.main import app  # noqa: E402
