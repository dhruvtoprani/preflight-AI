from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckpointStore:
    path: Path = field(
        default_factory=lambda: Path(tempfile.gettempdir())
        / "preflight-ai"
        / "ingestion_checkpoints.json"
    )
    values: dict[str, str] = field(default_factory=dict)

    def load(self) -> None:
        if not self.path.exists():
            self.values = {}
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            self.values = {str(key): str(value) for key, value in payload.items()}
        else:
            self.values = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str | None) -> None:
        if value is None:
            return
        self.values[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
