from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.bootstrap  # noqa: F401
from slack_bot.idempotency import IdempotencyStore


class IdempotencyTests(unittest.TestCase):
    def test_duplicate_key_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = IdempotencyStore(path=Path(temp_dir) / "idem.json", ttl_seconds=3600)
            first = store.reserve("key-1")
            second = store.reserve("key-1")

            self.assertFalse(first.is_duplicate)
            self.assertTrue(second.is_duplicate)


if __name__ == "__main__":
    unittest.main()
