from __future__ import annotations

import json
import logging
import os
import re

from fastapi import FastAPI, Header, HTTPException

from preflight_schemas import (
    InitiativeBrief,
    ReadinessStatus,
    ReviewRun,
    ReviewRunDashboardResponse,
    ReviewRunHistoryResponse,
)
from shared_utils.run_store import ReviewRunStore

from ingestion.main import sync_live_documents

from .engine import run_preflight
from .health import build_full_health_payload
from .runners import build_default_runner

app = FastAPI(title="PreFlight Orchestrator", version="0.1.0")
logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"\+?\d[\d\-\(\) ]{7,}\d")
_SLACK_ID_RE = re.compile(r"\b[UCDAW][A-Z0-9]{8,}\b")


@app.on_event("startup")
def startup_diagnostics() -> None:
    check_db = os.getenv("PREFLIGHT_PERSISTENCE_STARTUP_DB_CHECK", "false").lower() == "true"
    diagnostics = _run_store().persistence_diagnostics(check_connection=check_db)
    rendered = json.dumps(diagnostics, sort_keys=True)
    if diagnostics.get("status") == "ok":
        logger.info("persistence diagnostics: %s", rendered)
    else:
        logger.warning("persistence diagnostics: %s", rendered)


def _history_api_token() -> str:
    return os.getenv("PREFLIGHT_HISTORY_API_TOKEN", "").strip()


def _validate_history_auth(authorization: str | None) -> None:
    expected = _history_api_token()
    if not expected:
        return

    if not isinstance(authorization, str) or not authorization:
        raise HTTPException(status_code=401, detail="missing authorization")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="invalid authorization scheme")

    token = authorization[len(prefix) :].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="forbidden")


def _redact_text(value: str) -> str:
    redacted = _EMAIL_RE.sub("[redacted-email]", value)
    redacted = _PHONE_RE.sub("[redacted-phone]", redacted)
    redacted = _SLACK_ID_RE.sub("[redacted-id]", redacted)
    return redacted


def _sanitize_review_run(run: ReviewRun, include_sensitive: bool) -> ReviewRun:
    sanitized = run.model_copy(deep=True)

    sanitized.initiative_title = _redact_text(sanitized.initiative_title)

    if not include_sensitive:
        sanitized.requester = None
        sanitized.channel_id = None
        sanitized.thread_ts = None

    for review in sanitized.team_reviews:
        for concern in review.concerns:
            concern.statement = _redact_text(concern.statement)
            concern.blockers = [_redact_text(item) for item in concern.blockers]
            concern.questions = [_redact_text(item) for item in concern.questions]
            for evidence in concern.evidence:
                evidence.excerpt = _redact_text(evidence.excerpt)

    summary = sanitized.moderator_summary
    summary.blockers = [_redact_text(item) for item in summary.blockers]
    summary.dependencies = [_redact_text(item) for item in summary.dependencies]
    summary.questions_to_resolve = [_redact_text(item) for item in summary.questions_to_resolve]
    summary.suggested_owners = [_redact_text(item) for item in summary.suggested_owners]
    summary.kickoff_agenda = [_redact_text(item) for item in summary.kickoff_agenda]
    summary.warnings = [_redact_text(item) for item in summary.warnings]

    return sanitized


def _sanitize_history_response(
    payload: ReviewRunHistoryResponse,
    include_sensitive: bool,
) -> ReviewRunHistoryResponse:
    response = payload.model_copy(deep=True)
    for item in response.runs:
        item.initiative_title = _redact_text(item.initiative_title)
        if not include_sensitive:
            item.requester = None
            item.channel_id = None
            item.thread_ts = None
    return response


def _sanitize_dashboard_response(
    payload: ReviewRunDashboardResponse,
    include_sensitive: bool,
) -> ReviewRunDashboardResponse:
    response = payload.model_copy(deep=True)
    response.top_blockers = [_redact_text(item) for item in response.top_blockers]
    for item in response.recent_runs:
        item.initiative_title = _redact_text(item.initiative_title)
        if not include_sensitive:
            item.requester = None
            item.channel_id = None
            item.thread_ts = None
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/full")
def health_full() -> dict:
    return build_full_health_payload()


@app.post("/sync")
def sync() -> dict:
    result = sync_live_documents()
    return {
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
    }


def _run_store() -> ReviewRunStore:
    return ReviewRunStore()


@app.post("/review", response_model=ReviewRun)
def review(
    brief: InitiativeBrief,
    timeout_team: list[str] | None = None,
    sync_before_review: bool = False,
) -> ReviewRun:
    sync_warnings: list[str] = []
    if sync_before_review:
        sync_result = sync_live_documents()
        sync_warnings.extend(sync_result.warnings)

    runner = build_default_runner(timeout_teams=timeout_team or [])
    run = run_preflight(brief, runner=runner)

    if sync_warnings:
        run.moderator_summary.warnings.extend(sync_warnings)

    persist_result = _run_store().persist(run)
    if persist_result.warning and persist_result.warning not in run.moderator_summary.warnings:
        run.moderator_summary.warnings.append(persist_result.warning)

    return run


@app.get("/runs", response_model=ReviewRunHistoryResponse)
def list_review_runs(
    limit: int = 20,
    offset: int = 0,
    readiness: ReadinessStatus | None = None,
    team: str | None = None,
    initiative_contains: str | None = None,
    requester: str | None = None,
    include_sensitive: bool = False,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ReviewRunHistoryResponse:
    _validate_history_auth(authorization)
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    raw = _run_store().history(
        limit=safe_limit,
        offset=safe_offset,
        readiness=readiness.value if readiness else None,
        team=team,
        initiative_contains=initiative_contains,
        requester=requester,
    )
    return _sanitize_history_response(raw, include_sensitive=include_sensitive)


@app.get("/runs/dashboard", response_model=ReviewRunDashboardResponse)
def runs_dashboard(
    recent_limit: int = 10,
    team: str | None = None,
    initiative_contains: str | None = None,
    requester: str | None = None,
    include_sensitive: bool = False,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ReviewRunDashboardResponse:
    _validate_history_auth(authorization)
    safe_recent_limit = max(1, min(recent_limit, 50))
    raw = _run_store().dashboard(
        recent_limit=safe_recent_limit,
        team=team,
        initiative_contains=initiative_contains,
        requester=requester,
    )
    return _sanitize_dashboard_response(raw, include_sensitive=include_sensitive)


@app.get("/runs/{run_id}", response_model=ReviewRun)
def get_review_run(
    run_id: str,
    include_sensitive: bool = False,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ReviewRun:
    _validate_history_auth(authorization)
    run = _run_store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _sanitize_review_run(run, include_sensitive=include_sensitive)
