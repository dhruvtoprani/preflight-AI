from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.bootstrap  # noqa: F401
from preflight_schemas import InitiativeBrief, ModeratorSummary, ReadinessStatus, ReviewRun
from shared_utils.run_store import ReviewRunStore


def _sample_run(run_id: str = "run-1") -> ReviewRun:
    brief = InitiativeBrief(
        title="Automated pet health alerts",
        problem_statement="Users miss early warning signals for potential pet health changes.",
        proposed_solution="Generate proactive mobile alerts from health telemetry trends.",
        target_timeline="Q3",
        affected_teams=["engineering", "qa"],
        success_metric="Reduce time-to-notice by 30%",
        known_constraints=["Telemetry schema freeze in August"],
        requester="pm-1",
    )
    return ReviewRun(
        run_id=run_id,
        initiative_title=brief.title,
        requester=brief.requester,
        team_reviews=[],
        moderator_summary=ModeratorSummary(overall_readiness=ReadinessStatus.YELLOW),
    )


class RunStoreTests(unittest.TestCase):
    def test_prune_file_fallback_applies_age_and_count_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {
                "PREFLIGHT_RUN_FILE_RETENTION_DAYS": "1",
                "PREFLIGHT_RUN_FILE_MAX_FILES": "2",
            }
            with patch.dict(os.environ, env, clear=False):
                run_dir = Path(temp_dir)
                run_dir.mkdir(parents=True, exist_ok=True)

                old_path = run_dir / "old.json"
                old_path.write_text("{}", encoding="utf-8")
                stale_time = time.time() - (60 * 60 * 24 * 5)
                os.utime(old_path, (stale_time, stale_time))

                for idx in range(4):
                    path = run_dir / f"new-{idx}.json"
                    path.write_text("{}", encoding="utf-8")
                    time.sleep(0.01)

                store = ReviewRunStore(run_dir=run_dir, database_url="")
                result = store.prune_file_fallback()

                self.assertGreaterEqual(result["deleted_by_age"], 1)
                self.assertGreaterEqual(result["deleted_by_count"], 1)
                self.assertLessEqual(result["remaining"], 2)

    def test_persist_falls_back_to_file_when_postgres_driver_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ReviewRunStore(
                run_dir=Path(temp_dir),
                database_url="postgresql://localhost:5432/preflight",
            )

            with patch.object(store, "_db_client", return_value=None):
                persisted = store.persist(_sample_run("run-file-fallback"))

            self.assertEqual(persisted.stored_in, "file")
            self.assertTrue(persisted.path is not None)
            self.assertTrue(Path(persisted.path).exists())
            self.assertTrue(persisted.warning is not None)

    def test_persistence_diagnostics_reports_driver_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ReviewRunStore(
                run_dir=Path(temp_dir),
                database_url="postgresql://localhost:5432/preflight",
            )

            with patch.object(store, "_db_client", return_value=None):
                diagnostics = store.persistence_diagnostics(check_connection=True)

            self.assertEqual(diagnostics["status"], "degraded")
            self.assertTrue(diagnostics["database_url_configured"])
            self.assertTrue(diagnostics["database_url_is_postgres"])
            self.assertFalse(diagnostics["postgres_driver_installed"])
            self.assertEqual(diagnostics["storage_mode"], "file-fallback")
            self.assertTrue(any("psycopg" in warning for warning in diagnostics["warnings"]))


if __name__ == "__main__":
    unittest.main()
