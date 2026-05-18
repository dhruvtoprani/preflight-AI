from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from pydantic import BaseModel, Field, ValidationError

from preflight_schemas import InitiativeBrief, ReviewRun

from .formatter import format_thread_message
from .idempotency import IdempotencyStore
from .persistence import ReviewRunStore
from .service import run_review_and_notify
from .slack_client import SlackMessenger

app = FastAPI(title="PreFlight Slack Bot", version="0.1.0")


class IntakeResponse(BaseModel):
    run_id: str
    persisted_in: str
    persisted_path: str | None = None
    thread_preview: str
    warnings: list[str] = Field(default_factory=list)


def _sync_before_review_enabled() -> bool:
    return os.getenv("PREFLIGHT_SYNC_BEFORE_REVIEW", "false").lower() == "true"


def _should_use_background() -> bool:
    return os.getenv("PREFLIGHT_SLACK_ASYNC", "true").lower() == "true"


def _executor() -> ThreadPoolExecutor:
    max_workers = int(os.getenv("PREFLIGHT_SLACK_ASYNC_WORKERS", "4"))
    return ThreadPoolExecutor(max_workers=max_workers)


_executor_instance = _executor()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/full")
def health_full() -> dict:
    orchestrator_base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000")
    orchestrator_status = "missing"

    try:
        request = Request(url=f"{orchestrator_base_url}/health", method="GET")
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok":
                orchestrator_status = "ok"
    except Exception:  # noqa: BLE001
        orchestrator_status = "unreachable"

    checks = {
        "slack_bot_token": "ok" if os.getenv("SLACK_BOT_TOKEN") else "missing",
        "slack_signing_secret": "ok" if os.getenv("SLACK_SIGNING_SECRET") else "missing",
        "slack_app_token": "ok" if os.getenv("SLACK_APP_TOKEN") else "missing",
        "orchestrator_health": orchestrator_status,
    }

    status = "ok" if orchestrator_status == "ok" else "degraded"
    return {"status": status, "service": "slack-bot", "checks": checks}


@app.get("/config-check")
def config_check() -> dict[str, bool]:
    return {
        "has_slack_bot_token": bool(os.getenv("SLACK_BOT_TOKEN")),
        "has_slack_signing_secret": bool(os.getenv("SLACK_SIGNING_SECRET")),
        "has_slack_app_token": bool(os.getenv("SLACK_APP_TOKEN")),
    }


def call_orchestrator_review(
    brief: InitiativeBrief,
    timeout_team: list[str] | None = None,
    sync_before_review: bool | None = None,
) -> ReviewRun:
    orchestrator_base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000")
    sync_flag = _sync_before_review_enabled() if sync_before_review is None else sync_before_review
    query_string = urlencode(
        {
            "timeout_team": timeout_team or [],
            "sync_before_review": str(sync_flag).lower(),
        },
        doseq=True,
    )
    url = f"{orchestrator_base_url}/review"
    if query_string:
        url = f"{url}?{query_string}"

    request = Request(
        url=url,
        method="POST",
        data=json.dumps(brief.model_dump()).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"orchestrator returned {exc.code}: {detail}",
        )
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"orchestrator request failed: {exc}")

    return ReviewRun.model_validate(payload)


@app.post("/intake", response_model=IntakeResponse)
def intake(brief: InitiativeBrief, timeout_team: list[str] | None = None) -> IntakeResponse:
    run = call_orchestrator_review(
        brief=brief,
        timeout_team=timeout_team,
        sync_before_review=_sync_before_review_enabled(),
    )
    preview = format_thread_message(run)
    persist_result = ReviewRunStore().persist(run)

    return IntakeResponse(
        run_id=run.run_id,
        persisted_in=persist_result.stored_in,
        persisted_path=persist_result.path,
        thread_preview=preview,
        warnings=run.moderator_summary.warnings,
    )


class SlackEventResponse(BaseModel):
    status: str
    message: str


class SlackRequestBody(BaseModel):
    channel_id: str
    user_id: str
    text: str
    thread_ts: str | None = None


_KEY_ALIASES = {
    "title": "title",
    "problem": "problem_statement",
    "problem_statement": "problem_statement",
    "solution": "proposed_solution",
    "proposed_solution": "proposed_solution",
    "timeline": "target_timeline",
    "target_timeline": "target_timeline",
    "teams": "affected_teams",
    "affected_teams": "affected_teams",
    "metric": "success_metric",
    "success_metric": "success_metric",
    "constraints": "known_constraints",
    "known_constraints": "known_constraints",
}

_REQUIRED_FIELDS = [
    "title",
    "problem_statement",
    "proposed_solution",
    "target_timeline",
    "affected_teams",
    "success_metric",
]

_MENTION_RE = re.compile(r"<@[^>]+>")

_CANONICAL_TEAMS = [
    "engineering",
    "qa",
    "design",
    "support",
    "gtm",
    "security_privacy",
    "tpm",
]

_TEAM_ALIAS_MAP = {
    "security": "security_privacy",
    "privacy": "security_privacy",
    "security/privacy": "security_privacy",
    "sec": "security_privacy",
}


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_team_name(raw: str) -> str:
    normalized = raw.strip().lower().replace(" ", "_")
    return _TEAM_ALIAS_MAP.get(normalized, normalized)


def _parse_teams(value: str) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    invalid: list[str] = []
    for team in _parse_csv(value):
        normalized = _normalize_team_name(team)
        if normalized in _CANONICAL_TEAMS:
            if normalized not in selected:
                selected.append(normalized)
            continue
        invalid.append(team)
    return selected, invalid


def _build_structured_template(
    missing: list[str],
    details: list[str] | None = None,
    include_team_guidance: bool = False,
) -> str:
    display_map = {
        "problem_statement": "problem",
        "proposed_solution": "solution",
        "target_timeline": "timeline",
        "affected_teams": "teams",
        "success_metric": "metric",
        "known_constraints": "constraints",
    }
    missing_labels = [display_map.get(field, field) for field in missing]

    lines = [
        "Please send the initiative in this format:",
        "title: ...",
        "problem: ...",
        "solution: ...",
        "timeline: ...",
        "teams: engineering, qa, design, security_privacy",
        "metric: ...",
        "constraints: ...",
    ]
    if include_team_guidance or "affected_teams" in missing:
        lines.append(
            "Canonical teams: engineering, qa, design, support, gtm, security_privacy, tpm"
        )
        lines.append(
            "Alias mapping: security/privacy, security, privacy, sec -> security_privacy"
        )
        lines.append("Team format: use comma-separated values only")
    if missing_labels:
        lines.append(f"Missing fields: {', '.join(missing_labels)}")
    if details:
        lines.append(f"Validation issues: {' | '.join(details)}")

    return "\n".join(lines)


def _extract_structured_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        raw_key, raw_value = line.split(":", 1)
        canonical = _KEY_ALIASES.get(_normalize_key(raw_key))
        if canonical is None:
            continue
        fields[canonical] = raw_value.strip()
    return fields


def _parse_brief_from_text(
    text: str,
    user_id: str,
    channel_id: str,
    thread_ts: str | None,
) -> tuple[InitiativeBrief | None, str | None]:
    cleaned = _MENTION_RE.sub("", text).strip()
    fields = _extract_structured_fields(cleaned)

    missing = [field for field in _REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        return None, _build_structured_template(missing)

    teams, invalid_teams = _parse_teams(fields.get("affected_teams", ""))
    if invalid_teams:
        detail = (
            f"Unrecognized teams: {', '.join(invalid_teams)}. "
            f"Supported canonical teams: {', '.join(_CANONICAL_TEAMS)}"
        )
        return None, _build_structured_template(
            missing=[],
            details=[detail],
            include_team_guidance=True,
        )

    payload = {
        "title": fields.get("title", "").strip(),
        "problem_statement": fields.get("problem_statement", "").strip(),
        "proposed_solution": fields.get("proposed_solution", "").strip(),
        "target_timeline": fields.get("target_timeline", "").strip(),
        "affected_teams": teams,
        "success_metric": fields.get("success_metric", "").strip(),
        "known_constraints": _parse_csv(fields.get("known_constraints", "")),
        "requester": user_id,
        "channel_id": channel_id,
        "thread_ts": thread_ts,
    }

    try:
        return InitiativeBrief.model_validate(payload), None
    except ValidationError as exc:
        details: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []))
            msg = err.get("msg", "invalid")
            details.append(f"{loc}: {msg}")
        return None, _build_structured_template(missing=[], details=details)


def _execute_slack_review(brief: InitiativeBrief, timeout_team: list[str] | None = None) -> None:
    messenger = SlackMessenger()
    run_store = ReviewRunStore()
    idempotency_store = IdempotencyStore()

    def _review_runner(b: InitiativeBrief) -> ReviewRun:
        return call_orchestrator_review(
            brief=b,
            timeout_team=timeout_team,
            sync_before_review=_sync_before_review_enabled(),
        )

    run_review_and_notify(
        brief=brief,
        review_runner=_review_runner,
        messenger=messenger,
        run_store=run_store,
        idempotency_store=idempotency_store,
    )


@app.post("/slack/command", response_model=SlackEventResponse)
def slack_command(payload: SlackRequestBody) -> SlackEventResponse:
    brief, error = _parse_brief_from_text(
        text=payload.text,
        user_id=payload.user_id,
        channel_id=payload.channel_id,
        thread_ts=payload.thread_ts,
    )
    if brief is None:
        return SlackEventResponse(status="needs_input", message=error or "invalid brief")

    if _should_use_background():
        _executor_instance.submit(_execute_slack_review, brief)
        return SlackEventResponse(
            status="accepted",
            message="PreFlight review started. Results will be posted in thread.",
        )

    _execute_slack_review(brief)
    return SlackEventResponse(status="completed", message="PreFlight review completed.")


@app.post("/slack/events", response_model=SlackEventResponse)
async def slack_events(request: FastAPIRequest) -> SlackEventResponse:
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return SlackEventResponse(status="ok", message=payload.get("challenge", ""))

    event = payload.get("event", {})
    event_type = event.get("type")
    if event_type not in {"app_mention", "message"}:
        return SlackEventResponse(status="ignored", message="event type not handled")

    text = str(event.get("text", "")).strip()
    channel_id = event.get("channel")
    user_id = event.get("user", "unknown")
    thread_ts = event.get("thread_ts") or event.get("ts")

    if not channel_id or not text:
        return SlackEventResponse(status="ignored", message="missing channel/text")

    brief, error = _parse_brief_from_text(
        text=text,
        user_id=user_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
    )
    if brief is None:
        return SlackEventResponse(status="needs_input", message=error or "invalid brief")

    if _should_use_background():
        _executor_instance.submit(_execute_slack_review, brief)
        return SlackEventResponse(status="accepted", message="review started")

    _execute_slack_review(brief)
    return SlackEventResponse(status="completed", message="review completed")
