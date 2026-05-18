from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from preflight_schemas import (
    DashboardReadinessBreakdown,
    ReviewRun,
    ReviewRunDashboardResponse,
    ReviewRunHistoryResponse,
    ReviewRunListItem,
)


_RUN_TABLE_NAME = "preflight_review_runs"


@dataclass
class PersistResult:
    stored_in: str
    path: str | None = None
    warning: str | None = None


@dataclass
class _StoredRun:
    run: ReviewRun
    created_at: datetime


class ReviewRunStore:
    """Persist and query review runs with Postgres-first + file fallback behavior."""

    def __init__(
        self,
        run_dir: Path | None = None,
        database_url: str | None = None,
    ) -> None:
        default_run_dir = Path(tempfile.gettempdir()) / "preflight-ai" / "review_runs"
        self.run_dir = run_dir or Path(os.getenv("PREFLIGHT_RUN_DIR", default_run_dir))
        self.database_url = (database_url or os.getenv("DATABASE_URL", "")).strip()
        self.file_retention_days = self._env_int("PREFLIGHT_RUN_FILE_RETENTION_DAYS", 30)
        self.file_max_files = self._env_int("PREFLIGHT_RUN_FILE_MAX_FILES", 1000)
        self.db_connect_timeout_seconds = self._env_int("PREFLIGHT_DB_CONNECT_TIMEOUT_SECONDS", 3)

    def persist(self, run: ReviewRun) -> PersistResult:
        persisted_in_db, db_warning = self._try_db_persist(run)
        if persisted_in_db:
            return PersistResult(stored_in="db", path=None, warning=None)

        self.run_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.run_dir / f"{run.run_id}.json"
        envelope = {
            "created_at": self._normalize_dt(run.created_at).isoformat(),
            "run": run.model_dump(mode="json"),
        }
        target_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        self.prune_file_fallback()
        return PersistResult(stored_in="file", path=str(target_path), warning=db_warning)

    def get_run(self, run_id: str) -> ReviewRun | None:
        for stored in self._load_runs():
            if stored.run.run_id == run_id:
                return stored.run
        return None

    def history(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        readiness: str | None = None,
        team: str | None = None,
        initiative_contains: str | None = None,
        requester: str | None = None,
    ) -> ReviewRunHistoryResponse:
        filtered = self._filter_runs(
            self._load_runs(),
            readiness=readiness,
            team=team,
            initiative_contains=initiative_contains,
            requester=requester,
        )
        total = len(filtered)
        window = filtered[offset : offset + limit]

        return ReviewRunHistoryResponse(
            total=total,
            runs=[self._to_list_item(item) for item in window],
        )

    def dashboard(
        self,
        *,
        recent_limit: int = 10,
        team: str | None = None,
        initiative_contains: str | None = None,
        requester: str | None = None,
    ) -> ReviewRunDashboardResponse:
        filtered = self._filter_runs(
            self._load_runs(),
            team=team,
            initiative_contains=initiative_contains,
            requester=requester,
        )

        readiness_counter = Counter(
            item.run.moderator_summary.overall_readiness.value for item in filtered
        )
        blocker_counter = Counter(
            blocker
            for item in filtered
            for blocker in item.run.moderator_summary.blockers
            if blocker.strip()
        )

        return ReviewRunDashboardResponse(
            total_runs=len(filtered),
            readiness=DashboardReadinessBreakdown(
                green=readiness_counter.get("green", 0),
                yellow=readiness_counter.get("yellow", 0),
                red=readiness_counter.get("red", 0),
            ),
            top_blockers=[blocker for blocker, _count in blocker_counter.most_common(5)],
            recent_runs=[self._to_list_item(item) for item in filtered[:recent_limit]],
        )

    def prune_file_fallback(self) -> dict[str, int]:
        if not self.run_dir.exists():
            return {
                "deleted_by_age": 0,
                "deleted_by_count": 0,
                "remaining": 0,
            }

        deleted_by_age = 0
        deleted_by_count = 0

        paths = self._file_paths_sorted_newest_first()

        if self.file_retention_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.file_retention_days)
            for path in paths:
                modified = self._normalize_dt(
                    datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                )
                if modified >= cutoff:
                    continue
                try:
                    path.unlink()
                    deleted_by_age += 1
                except OSError:
                    continue

        paths = self._file_paths_sorted_newest_first()
        if self.file_max_files > 0 and len(paths) > self.file_max_files:
            for path in paths[self.file_max_files :]:
                try:
                    path.unlink()
                    deleted_by_count += 1
                except OSError:
                    continue

        remaining = len(self._file_paths_sorted_newest_first())
        return {
            "deleted_by_age": deleted_by_age,
            "deleted_by_count": deleted_by_count,
            "remaining": remaining,
        }

    def persistence_diagnostics(self, *, check_connection: bool = False) -> dict[str, Any]:
        postgres_url = self._is_postgres_url()
        psycopg = self._db_client()
        postgres_driver_installed = psycopg is not None

        writable, writable_error = self._is_run_dir_writable()

        warnings: list[str] = []
        status = "ok"

        postgres_connection = "skipped"
        if self.database_url and postgres_url and not postgres_driver_installed:
            warnings.append("DATABASE_URL targets Postgres but psycopg is not installed.")
            status = "degraded"
        elif self.database_url and not postgres_url:
            warnings.append("DATABASE_URL is set but not a Postgres URL; file fallback is active.")
            status = "degraded"

        if check_connection and postgres_url and postgres_driver_installed:
            connected, error = self._can_connect_db()
            if connected:
                postgres_connection = "ok"
            else:
                postgres_connection = "failed"
                status = "degraded"
                warnings.append(f"Postgres connectivity check failed: {error}")

        if not writable:
            status = "degraded"
            warnings.append(f"Run fallback directory is not writable: {writable_error}")

        storage_mode = "db" if postgres_url and postgres_driver_installed else "file-fallback"

        return {
            "status": status,
            "storage_mode": storage_mode,
            "database_url_configured": bool(self.database_url),
            "database_url_is_postgres": postgres_url,
            "postgres_driver_installed": postgres_driver_installed,
            "postgres_connection": postgres_connection,
            "run_dir": str(self.run_dir),
            "run_dir_writable": writable,
            "run_file_retention_days": self.file_retention_days,
            "run_file_max_files": self.file_max_files,
            "warnings": warnings,
        }

    def _filter_runs(
        self,
        runs: list[_StoredRun],
        *,
        readiness: str | None = None,
        team: str | None = None,
        initiative_contains: str | None = None,
        requester: str | None = None,
    ) -> list[_StoredRun]:
        readiness_value = readiness.strip().lower() if readiness else None
        team_value = team.strip().lower() if team else None
        initiative_value = (
            initiative_contains.strip().lower() if initiative_contains else None
        )
        requester_value = requester.strip().lower() if requester else None

        def _matches(item: _StoredRun) -> bool:
            run = item.run
            if (
                readiness_value
                and run.moderator_summary.overall_readiness.value != readiness_value
            ):
                return False
            if team_value and not any(
                review.team.strip().lower() == team_value for review in run.team_reviews
            ):
                return False
            if initiative_value and initiative_value not in run.initiative_title.lower():
                return False
            if requester_value and (run.requester or "").strip().lower() != requester_value:
                return False
            return True

        return [item for item in runs if _matches(item)]

    def _to_list_item(self, item: _StoredRun) -> ReviewRunListItem:
        run = item.run
        return ReviewRunListItem(
            run_id=run.run_id,
            created_at=item.created_at,
            initiative_title=run.initiative_title,
            overall_readiness=run.moderator_summary.overall_readiness,
            teams=[review.team for review in run.team_reviews],
            blocker_count=len(run.moderator_summary.blockers),
            warning_count=len(run.moderator_summary.warnings),
            requester=run.requester,
            channel_id=run.channel_id,
            thread_ts=run.thread_ts,
        )

    def _load_runs(self) -> list[_StoredRun]:
        db_runs = self._load_runs_from_db()
        if db_runs is not None:
            return db_runs
        return self._load_runs_from_files()

    def _file_paths_sorted_newest_first(self) -> list[Path]:
        return sorted(
            self.run_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def _load_runs_from_files(self) -> list[_StoredRun]:
        if not self.run_dir.exists():
            return []

        runs: list[_StoredRun] = []
        for path in self._file_paths_sorted_newest_first():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            created_at = self._normalize_dt(
                datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            )
            run_payload: Any = payload
            if isinstance(payload, dict) and isinstance(payload.get("run"), dict):
                run_payload = payload["run"]
                maybe_created = self._parse_dt(payload.get("created_at"))
                if maybe_created is not None:
                    created_at = maybe_created

            try:
                run = ReviewRun.model_validate(run_payload)
            except Exception:  # noqa: BLE001
                continue

            if isinstance(run_payload, dict) and not run_payload.get("created_at"):
                run.created_at = created_at

            runs.append(
                _StoredRun(
                    run=run,
                    created_at=self._normalize_dt(run.created_at),
                )
            )

        runs.sort(key=lambda item: item.created_at, reverse=True)
        return runs

    def _is_postgres_url(self) -> bool:
        return self.database_url.startswith("postgresql://") or self.database_url.startswith(
            "postgres://"
        )

    def _db_client(self):
        if not self._is_postgres_url():
            return None
        try:
            import psycopg  # type: ignore

            return psycopg
        except Exception:  # noqa: BLE001
            return None

    def _is_run_dir_writable(self) -> tuple[bool, str | None]:
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            probe = self.run_dir / ".preflight_write_probe"
            probe.write_text("ok", encoding="utf-8")
            if probe.exists():
                probe.unlink()
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _can_connect_db(self) -> tuple[bool, str | None]:
        psycopg = self._db_client()
        if psycopg is None:
            return False, "psycopg is not available"

        try:
            with psycopg.connect(
                self.database_url,
                connect_timeout=self.db_connect_timeout_seconds,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _ensure_table(self, cursor) -> None:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_RUN_TABLE_NAME} (
                run_id TEXT PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL,
                initiative_title TEXT NOT NULL,
                requester TEXT NULL,
                channel_id TEXT NULL,
                thread_ts TEXT NULL,
                overall_readiness TEXT NOT NULL,
                warnings_count INTEGER NOT NULL,
                payload JSONB NOT NULL
            );
            """
        )

    def _try_db_persist(self, run: ReviewRun) -> tuple[bool, str | None]:
        psycopg = self._db_client()
        if psycopg is None:
            if self._is_postgres_url():
                return (
                    False,
                    "postgres persistence unavailable (install psycopg); file fallback used",
                )
            return False, None

        payload_json = run.model_dump_json()
        created_at = self._normalize_dt(run.created_at)
        try:
            with psycopg.connect(
                self.database_url,
                connect_timeout=self.db_connect_timeout_seconds,
            ) as conn:
                with conn.cursor() as cur:
                    self._ensure_table(cur)
                    cur.execute(
                        f"""
                        INSERT INTO {_RUN_TABLE_NAME} (
                            run_id,
                            created_at,
                            initiative_title,
                            requester,
                            channel_id,
                            thread_ts,
                            overall_readiness,
                            warnings_count,
                            payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (run_id)
                        DO UPDATE SET
                            created_at = EXCLUDED.created_at,
                            initiative_title = EXCLUDED.initiative_title,
                            requester = EXCLUDED.requester,
                            channel_id = EXCLUDED.channel_id,
                            thread_ts = EXCLUDED.thread_ts,
                            overall_readiness = EXCLUDED.overall_readiness,
                            warnings_count = EXCLUDED.warnings_count,
                            payload = EXCLUDED.payload;
                        """,
                        (
                            run.run_id,
                            created_at,
                            run.initiative_title,
                            run.requester,
                            run.channel_id,
                            run.thread_ts,
                            run.moderator_summary.overall_readiness.value,
                            len(run.moderator_summary.warnings),
                            payload_json,
                        ),
                    )
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, f"postgres persistence failed ({exc}); file fallback used"

    def _load_runs_from_db(self) -> list[_StoredRun] | None:
        psycopg = self._db_client()
        if psycopg is None:
            return None

        try:
            with psycopg.connect(
                self.database_url,
                connect_timeout=self.db_connect_timeout_seconds,
            ) as conn:
                with conn.cursor() as cur:
                    self._ensure_table(cur)
                    cur.execute(
                        f"""
                        SELECT payload, created_at
                        FROM {_RUN_TABLE_NAME}
                        ORDER BY created_at DESC;
                        """
                    )
                    rows = cur.fetchall()
        except Exception:  # noqa: BLE001
            return None

        stored_runs: list[_StoredRun] = []
        for payload, created_at in rows:
            payload_dict = payload if isinstance(payload, dict) else json.loads(payload)
            try:
                run = ReviewRun.model_validate(payload_dict)
            except Exception:  # noqa: BLE001
                continue
            created = self._normalize_dt(self._parse_dt(created_at) or run.created_at)
            run.created_at = created
            stored_runs.append(_StoredRun(run=run, created_at=created))
        return stored_runs

    def _parse_dt(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return self._normalize_dt(value)
        if isinstance(value, str):
            cleaned = value.strip().replace("Z", "+00:00")
            if not cleaned:
                return None
            try:
                return self._normalize_dt(datetime.fromisoformat(cleaned))
            except ValueError:
                return None
        return None

    def _normalize_dt(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _env_int(self, key: str, default: int) -> int:
        raw = os.getenv(key)
        if raw is None or raw.strip() == "":
            return default
        try:
            return max(0, int(raw))
        except ValueError:
            return default
