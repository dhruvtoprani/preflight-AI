from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATHS = [
    ROOT / "packages/schemas/src",
    ROOT / "packages/shared-utils/src",
]

for src_path in reversed(SRC_PATHS):
    src_string = str(src_path)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)

from shared_utils.run_store import ReviewRunStore  # noqa: E402


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    check_db = _as_bool("PREFLIGHT_PERSISTENCE_HEALTH_DB_CHECK", True)
    strict = _as_bool("PREFLIGHT_PERSISTENCE_STRICT", False)

    diagnostics = ReviewRunStore().persistence_diagnostics(check_connection=check_db)
    print(json.dumps(diagnostics, indent=2, sort_keys=True))

    if strict and diagnostics.get("status") != "ok":
        raise SystemExit(1)
