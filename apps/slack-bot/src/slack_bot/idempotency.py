from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IdempotencyResult:
    is_duplicate: bool
    key: str


class IdempotencyStore:
    def __init__(self, path: Path | None = None, ttl_seconds: int = 6 * 60 * 60) -> None:
        self.path = path or (Path(tempfile.gettempdir()) / "preflight-ai" / "slack_idempotency.json")
        self.ttl_seconds = ttl_seconds

    def _load(self) -> dict[str, float]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {str(k): float(v) for k, v in payload.items()}
        except Exception:  # noqa: BLE001
            return {}
        return {}

    def _save(self, data: dict[str, float]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def reserve(self, key: str) -> IdempotencyResult:
        now = time.time()
        records = self._load()

        active = {
            existing_key: ts
            for existing_key, ts in records.items()
            if now - ts < self.ttl_seconds
        }

        if key in active:
            self._save(active)
            return IdempotencyResult(is_duplicate=True, key=key)

        active[key] = now
        self._save(active)
        return IdempotencyResult(is_duplicate=False, key=key)
