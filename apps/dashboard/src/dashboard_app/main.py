from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from orchestrator.engine import run_preflight
from orchestrator.moderator import DeterministicModerator
from orchestrator.runners import DeterministicRunner
from preflight_schemas import InitiativeBrief, ReviewRun
from slack_bot.formatter import format_thread_message

app = FastAPI(title="PreFlight", version="0.1.0")


def _history_auth_token() -> str:
    return os.getenv("PREFLIGHT_HISTORY_API_TOKEN", "").strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _orchestrator_base_url() -> str:
    return os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000").rstrip("/")


def _fetch_json(path: str, query: dict[str, str] | None = None) -> dict:
    suffix = path
    if query:
        suffix = f"{suffix}?{urlencode(query)}"

    headers = {}
    token = _history_auth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url=f"{_orchestrator_base_url()}{suffix}",
        method="GET",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"orchestrator returned {exc.code}: {detail}",
        )
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"orchestrator request failed: {exc}")


def _demo_brief_dir() -> Path:
    return _repo_root() / "docs" / "pilot" / "demo_briefs"


def _load_demo_briefs() -> list[InitiativeBrief]:
    paths = sorted(_demo_brief_dir().glob("*.json"))
    briefs: list[InitiativeBrief] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        briefs.append(InitiativeBrief.model_validate(payload))
    return briefs


def _evidence_ratio(run: ReviewRun) -> float:
    concerns = [concern for review in run.team_reviews for concern in review.concerns]
    if not concerns:
        return 1.0
    evidence_backed = [
        concern
        for concern in concerns
        if concern.evidence_status.value == "evidence-backed"
    ]
    return round(len(evidence_backed) / len(concerns), 4)


def _review_run_to_demo_payload(run: ReviewRun) -> dict:
    summary = run.moderator_summary
    return {
        "run": run.model_dump(mode="json"),
        "slack_message": format_thread_message(run),
        "metrics": {
            "team_count": len(run.team_reviews),
            "concern_count": sum(len(review.concerns) for review in run.team_reviews),
            "blocker_count": len(summary.blockers),
            "question_count": len(summary.questions_to_resolve),
            "evidence_backed_ratio": _evidence_ratio(run),
        },
    }


def _build_demo_runs() -> list[dict]:
    runner = DeterministicRunner()
    moderator = DeterministicModerator()
    return [
        _review_run_to_demo_payload(
            run_preflight(brief, runner=runner, moderator=moderator)
        )
        for brief in _load_demo_briefs()
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico")
def favicon() -> Response:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#1264a3"/>'
        '<path d="M8 10h16v3H8zM8 15h11v3H8zM8 20h14v3H8z" fill="#fff"/>'
        "</svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/health/full")
def health_full() -> dict:
    orchestrator_status = "unreachable"
    try:
        payload = _fetch_json("/health")
        if payload.get("status") == "ok":
            orchestrator_status = "ok"
    except HTTPException:
        orchestrator_status = "unreachable"

    status = "ok" if orchestrator_status == "ok" else "degraded"
    return {
        "status": status,
        "service": "dashboard",
        "checks": {
            "orchestrator_health": orchestrator_status,
        },
    }


@app.get("/api/dashboard")
def api_dashboard(
    recent_limit: int = 10,
    list_limit: int = 25,
    readiness: str | None = None,
    team: str | None = None,
    requester: str | None = None,
    initiative_contains: str | None = None,
) -> dict:
    dashboard_query = {
        "recent_limit": str(max(1, min(recent_limit, 50))),
    }
    list_query = {
        "limit": str(max(1, min(list_limit, 200))),
    }

    if team:
        dashboard_query["team"] = team
        list_query["team"] = team
    if requester:
        dashboard_query["requester"] = requester
        list_query["requester"] = requester
    if initiative_contains:
        dashboard_query["initiative_contains"] = initiative_contains
        list_query["initiative_contains"] = initiative_contains
    if readiness:
        list_query["readiness"] = readiness

    dashboard = _fetch_json("/runs/dashboard", query=dashboard_query)
    runs = _fetch_json("/runs", query=list_query)

    return {
        "dashboard": dashboard,
        "runs": runs,
        "filters": {
            "readiness": readiness,
            "team": team,
            "requester": requester,
            "initiative_contains": initiative_contains,
        },
    }


@app.get("/api/runs/{run_id}")
def api_run_detail(run_id: str) -> dict:
    return _fetch_json(f"/runs/{run_id}")


@app.get("/api/demo")
def api_demo() -> dict:
    demos = _build_demo_runs()
    aggregate_concerns = sum(item["metrics"]["concern_count"] for item in demos)
    aggregate_evidence = sum(
        int(item["metrics"]["evidence_backed_ratio"] * item["metrics"]["concern_count"])
        for item in demos
    )
    evidence_ratio = 1.0
    if aggregate_concerns:
        evidence_ratio = round(aggregate_evidence / aggregate_concerns, 4)

    return {
        "scenario_count": len(demos),
        "evidence_backed_ratio": evidence_ratio,
        "scenarios": demos,
    }


@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PreFlight Slack Demo</title>
    <style>
      :root {
        --sidebar: #351039;
        --sidebar-2: #210923;
        --accent: #1264a3;
        --green: #0b7a3b;
        --yellow: #9f6400;
        --red: #b3261e;
        --ink: #1d1c1d;
        --muted: #616061;
        --line: #e8e4e8;
        --soft: #f8f8f8;
        --chip: #eef5fb;
        --shadow: 0 18px 45px rgba(29, 28, 29, 0.12);
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background: #fff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .boot {
        position: fixed;
        inset: 0;
        z-index: 50;
        display: grid;
        place-items: center;
        padding: 24px;
        color: #fff;
        background: linear-gradient(135deg, rgba(53, 16, 57, 0.96), rgba(18, 100, 163, 0.96)), #351039;
        transition: opacity 360ms ease, visibility 360ms ease;
      }

      .boot.hidden {
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
      }

      .boot-card {
        width: min(420px, 100%);
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 14px;
        padding: 18px;
        background: rgba(255, 255, 255, 0.12);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
        backdrop-filter: blur(20px);
      }

      .boot-top {
        display: grid;
        grid-template-columns: 48px minmax(0, 1fr);
        gap: 12px;
        align-items: center;
      }

      .boot-mark {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        color: #1264a3;
        background: #fff;
        font-weight: 900;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);
      }

      .boot-title {
        font-weight: 850;
        font-size: 1.05rem;
      }

      .boot-subtitle {
        margin-top: 4px;
        color: rgba(255, 255, 255, 0.78);
        font-size: 0.9rem;
      }

      .boot-bar {
        height: 6px;
        border-radius: 999px;
        margin: 18px 0 12px;
        background: rgba(255, 255, 255, 0.18);
        overflow: hidden;
      }

      .boot-bar span {
        display: block;
        height: 100%;
        width: 46%;
        border-radius: inherit;
        background: linear-gradient(90deg, #2eb67d, #ecb22e, #36c5f0);
        animation: bootLoad 1.2s ease-in-out infinite alternate;
      }

      .boot-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 7px;
      }

      .boot-pills span {
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 999px;
        padding: 5px 8px;
        color: rgba(255, 255, 255, 0.82);
        font-size: 0.78rem;
        background: rgba(255, 255, 255, 0.1);
      }

      .workspace {
        min-height: 100vh;
        display: grid;
        grid-template-columns: 260px minmax(0, 1fr);
      }

      .sidebar {
        background: linear-gradient(180deg, var(--sidebar), var(--sidebar-2));
        color: #fff;
        padding: 18px 14px;
        box-shadow: inset -1px 0 rgba(255, 255, 255, 0.08);
      }

      .workspace-name {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 800;
        font-size: 1.08rem;
        margin-bottom: 18px;
      }

      .status-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #2eb67d;
        display: inline-block;
        margin-right: 7px;
      }

      .side-section {
        margin-top: 20px;
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
      }

      .channel-list {
        list-style: none;
        margin: 8px 0 0;
        padding: 0;
        display: grid;
        gap: 4px;
      }

      .channel-list li {
        border-radius: 6px;
        padding: 7px 8px;
        color: rgba(255, 255, 255, 0.82);
      }

      .channel-list li.active {
        color: #fff;
        background: rgba(255, 255, 255, 0.18);
        font-weight: 700;
      }

      .main {
        min-width: 0;
        display: grid;
        grid-template-rows: auto 1fr auto;
        min-height: 100vh;
      }

      .channel-header {
        border-bottom: 1px solid var(--line);
        padding: 12px 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(14px);
      }

      .channel-title {
        margin: 0;
        font-size: 1.14rem;
      }

      .channel-topic {
        color: var(--muted);
        margin-top: 3px;
        font-size: 0.9rem;
      }

      .header-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-end;
      }

      .button {
        border: 1px solid var(--line);
        background: #fff;
        color: var(--ink);
        border-radius: 6px;
        padding: 7px 10px;
        font-weight: 700;
        cursor: pointer;
      }

      .button.primary {
        color: #fff;
        background: var(--accent);
        border-color: var(--accent);
      }

      .conversation {
        overflow: auto;
        padding: 14px 0 22px;
      }

      .intro {
        padding: 0 22px 14px;
        border-bottom: 1px solid var(--line);
        margin-bottom: 14px;
      }

      .intro h1 {
        margin: 0;
        font-size: 1.42rem;
        line-height: 1.15;
      }

      .intro p {
        margin: 6px 0 0;
        max-width: 640px;
        color: var(--muted);
        line-height: 1.42;
      }

      .metrics {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin-top: 16px;
        max-width: 940px;
      }

      .metric {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 9px 10px;
        min-height: 68px;
        background: var(--soft);
        transition: transform 140ms ease, border-color 140ms ease;
      }

      .metric:hover {
        transform: translateY(-1px);
        border-color: rgba(18, 100, 163, 0.22);
      }

      .metric span {
        color: var(--muted);
        font-size: 0.8rem;
      }

      .metric strong {
        display: block;
        font-size: 1.35rem;
        margin-top: 5px;
      }

      .message {
        display: grid;
        grid-template-columns: 42px minmax(0, 1fr);
        gap: 10px;
        padding: 9px 22px;
      }

      .message:hover { background: #f8f8f8; }
      .message.compact { padding-top: 5px; padding-bottom: 5px; }

      .avatar {
        width: 38px;
        height: 38px;
        border-radius: 8px;
        display: grid;
        place-items: center;
        font-weight: 800;
        color: #fff;
      }

      .avatar.pm { background: #611f69; }
      .avatar.bot { background: #1264a3; }

      .meta {
        display: flex;
        align-items: baseline;
        gap: 7px;
        margin-bottom: 3px;
      }

      .name { font-weight: 800; }
      .time { color: var(--muted); font-size: 0.78rem; }

      .text {
        line-height: 1.45;
        white-space: pre-wrap;
      }

      .brief {
        border: 1px solid var(--line);
        border-left: 4px solid #611f69;
        border-radius: 8px;
        padding: 9px 10px;
        background: #fff;
        max-width: 720px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.86rem;
      }

      .option-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
        max-width: 940px;
        margin-top: 8px;
      }

      .option-card {
        appearance: none;
        text-align: left;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 249, 249, 0.98));
        padding: 11px;
        cursor: pointer;
        font: inherit;
        min-height: 108px;
        position: relative;
        overflow: hidden;
        transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
      }

      .option-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 4px;
        background: var(--accent);
      }

      .option-card[data-tone="green"]::before { background: #2eb67d; }
      .option-card[data-tone="yellow"]::before { background: #ecb22e; }
      .option-card[data-tone="blue"]::before { background: #36c5f0; }

      .option-card:hover,
      .option-card:focus-visible {
        border-color: rgba(18, 100, 163, 0.45);
        box-shadow: 0 8px 22px rgba(18, 100, 163, 0.12);
        transform: translateY(-1px);
        outline: none;
      }

      .option-card strong {
        display: block;
        margin-bottom: 5px;
      }

      .option-card .option-kicker {
        display: block;
        color: var(--accent);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0;
        margin-bottom: 6px;
        text-transform: uppercase;
      }

      .option-card span {
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.35;
      }

      .triage {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fff;
        max-width: 760px;
        padding: 11px;
        display: grid;
        gap: 9px;
        box-shadow: 0 10px 26px rgba(18, 100, 163, 0.08);
      }

      .triage-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }

      .triage-title {
        font-weight: 800;
      }

      .triage-score {
        color: var(--muted);
        font-size: 0.82rem;
      }

      .triage-progress {
        height: 5px;
        border-radius: 999px;
        background: #ece9ec;
        overflow: hidden;
      }

      .triage-progress span {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, #2eb67d, #36c5f0);
        transition: width 260ms ease;
      }

      .source-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .source-chip {
        border: 1px solid #d9e6ee;
        border-radius: 999px;
        padding: 4px 8px;
        color: #24475a;
        background: #f3f8fb;
        font-size: 0.78rem;
      }

      .source-step {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--muted);
        font-size: 0.9rem;
      }

      .pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #2eb67d;
        box-shadow: 0 0 0 0 rgba(46, 182, 125, 0.45);
        animation: pulse 1.15s infinite;
        flex: 0 0 auto;
      }

      .check {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #2eb67d;
        color: #fff;
        display: grid;
        place-items: center;
        font-size: 0.7rem;
        font-weight: 900;
        flex: 0 0 auto;
      }

      .typing {
        display: inline-flex;
        gap: 4px;
        align-items: center;
        padding: 8px 10px;
        border-radius: 14px;
        background: var(--soft);
      }

      .typing span {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #8d8a8d;
        animation: bounce 1s infinite ease-in-out;
      }

      .typing span:nth-child(2) { animation-delay: 120ms; }
      .typing span:nth-child(3) { animation-delay: 240ms; }

      @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(46, 182, 125, 0.45); }
        70% { box-shadow: 0 0 0 9px rgba(46, 182, 125, 0); }
        100% { box-shadow: 0 0 0 0 rgba(46, 182, 125, 0); }
      }

      @keyframes bounce {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
        40% { transform: translateY(-3px); opacity: 1; }
      }

      @keyframes bootLoad {
        from { transform: translateX(-18%); width: 38%; }
        to { transform: translateX(125%); width: 58%; }
      }

      .review {
        border: 1px solid var(--line);
        border-radius: 8px;
        max-width: 940px;
        background: #fff;
        overflow: hidden;
        box-shadow: var(--shadow);
      }

      .review-head {
        padding: 12px;
        border-bottom: 1px solid var(--line);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }

      .review-title {
        font-weight: 800;
      }

      .readiness {
        border-radius: 999px;
        padding: 4px 9px;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
      }

      .readiness.green { color: var(--green); background: #edf8f1; }
      .readiness.yellow { color: var(--yellow); background: #fff6df; }
      .readiness.red { color: var(--red); background: #fff0ef; }

      .review-body {
        padding: 12px;
        display: grid;
        gap: 10px;
      }

      .section-title {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 5px;
      }

      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .chip {
        background: var(--chip);
        border: 1px solid #d2e3f1;
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 0.82rem;
      }

      .team-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
      }

      .team-card {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px;
        background: #fbfbfb;
      }

      .team-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 7px;
      }

      .evidence {
        margin-top: 8px;
        color: var(--muted);
        font-size: 0.84rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .composer {
        border-top: 1px solid var(--line);
        padding: 12px 18px 18px;
        background: #fff;
      }

      .composer-box {
        border: 1px solid #b9b5b9;
        border-radius: 8px;
        min-height: 54px;
        padding: 10px;
        color: var(--muted);
        transition: border-color 160ms ease, box-shadow 160ms ease;
      }

      .composer-box.active {
        border-color: rgba(18, 100, 163, 0.5);
        box-shadow: 0 0 0 3px rgba(18, 100, 163, 0.1);
      }

      a { color: var(--accent); }

      @media (max-width: 860px) {
        .workspace { grid-template-columns: 1fr; }
        .sidebar { display: none; }
        .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .option-grid { grid-template-columns: 1fr; }
        .team-grid { grid-template-columns: 1fr; }
        .channel-header { align-items: flex-start; flex-direction: column; }
      }

      @media (max-width: 560px) {
        .metrics { grid-template-columns: 1fr; }
        .message { grid-template-columns: 34px minmax(0, 1fr); padding: 10px 14px; }
        .avatar { width: 32px; height: 32px; border-radius: 7px; font-size: 0.82rem; }
      }
    </style>
  </head>
  <body>
    <div class="boot" id="bootLoader" aria-live="polite">
      <div class="boot-card">
        <div class="boot-top">
          <div class="boot-mark">PF</div>
          <div>
            <div class="boot-title">Opening #preflight-demo</div>
            <div class="boot-subtitle">Syncing source graph</div>
          </div>
        </div>
        <div class="boot-bar"><span></span></div>
        <div class="boot-pills"><span>Jira</span><span>Confluence</span><span>Roadmap</span><span>Team lenses</span></div>
      </div>
    </div>
    <div class="workspace">
      <aside class="sidebar">
        <div class="workspace-name"><span><span class="status-dot"></span>PreFlight HQ</span><span>v0.1</span></div>
        <div class="side-section">Channels</div>
        <ul class="channel-list">
          <li># product-kickoff</li>
          <li class="active"># preflight-demo</li>
          <li># launch-readiness</li>
          <li># qa-release-room</li>
        </ul>
        <div class="side-section">Pilot Kit</div>
        <ul class="channel-list">
          <li>Runbook</li>
          <li>Demo briefs</li>
          <li>Baseline metrics</li>
        </ul>
      </aside>

      <main class="main">
        <header class="channel-header">
          <div>
            <h2 class="channel-title"># preflight-demo</h2>
            <div class="channel-topic">Kickoff readiness before the room is booked.</div>
          </div>
          <div class="header-actions">
            <button class="button primary" id="resetDemo">Reset</button>
          </div>
        </header>

        <section class="conversation">
          <div class="intro">
            <h1>Kickoff risks, in a Slack thread.</h1>
            <p>Pick a brief. Watch PreFlight triage sources and send the thread.</p>
            <div class="metrics">
              <div class="metric"><span>Demo scenarios</span><strong id="scenarioCount">-</strong></div>
              <div class="metric"><span>Evidence-backed ratio</span><strong id="evidenceRatio">-</strong></div>
              <div class="metric"><span>Current readiness</span><strong id="currentReadiness">-</strong></div>
              <div class="metric"><span>Open blockers</span><strong id="currentBlockers">-</strong></div>
            </div>
          </div>

          <div id="messages"></div>
        </section>

        <footer class="composer">
          <div class="composer-box" id="composerText">Choose a kickoff brief above...</div>
        </footer>
      </main>
    </div>

    <script>
      const state = { scenarios: [], active: null, timers: [] };

      const els = {
        messages: document.getElementById('messages'),
        bootLoader: document.getElementById('bootLoader'),
        scenarioCount: document.getElementById('scenarioCount'),
        evidenceRatio: document.getElementById('evidenceRatio'),
        currentReadiness: document.getElementById('currentReadiness'),
        currentBlockers: document.getElementById('currentBlockers'),
        resetDemo: document.getElementById('resetDemo'),
        composerText: document.getElementById('composerText'),
      };

      function esc(value) {
        return String(value ?? '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#039;');
      }

      function titleTeam(team) {
        const map = { qa: 'QA', gtm: 'GTM', tpm: 'TPM', security_privacy: 'Security/Privacy' };
        return map[team] || String(team).replaceAll('_', ' ').replace(/\\b\\w/g, (c) => c.toUpperCase());
      }

      function briefText(run) {
        const teams = (run.team_reviews || []).map((review) => review.team).join(', ');
        return [
          `title: ${run.initiative_title}`,
          `teams: ${teams}`,
          `requester: ${run.requester || 'pilot-pm'}`,
          'format: readiness review + blockers + owner map + agenda'
        ].join('\\n');
      }

      function optionCopy(run) {
        const title = run.initiative_title || '';
        if (title.includes('health alerts')) {
          return ['Launch check', 'Health alerts launch', 'Check ownership, QA coverage, and support readiness.', 'green'];
        }
        if (title.includes('migration')) {
          return ['Risk scan', 'Legacy migration', 'Find sequencing, rollback, and privacy gaps.', 'blue'];
        }
        return ['Red-team', 'Compressed release', 'Pressure-test the date, GTM gates, and beta risk.', 'yellow'];
      }

      function listBlock(title, values) {
        const items = values && values.length ? values : ['None captured'];
        return `<div><div class="section-title">${esc(title)}</div><div class="chips">${items.map((value) => `<span class="chip">${esc(value)}</span>`).join('')}</div></div>`;
      }

      function renderReview(run) {
        const summary = run.moderator_summary || {};
        const readiness = summary.overall_readiness || 'yellow';
        const teams = run.team_reviews || [];
        return `
          <div class="review">
            <div class="review-head">
              <div class="review-title">${esc(run.initiative_title)}</div>
              <span class="readiness ${esc(readiness)}">${esc(readiness)}</span>
            </div>
            <div class="review-body">
              ${listBlock('Before kickoff, resolve', summary.blockers)}
              ${listBlock('Suggested owners', summary.suggested_owners)}
              <div>
                <div class="section-title">Team perspectives</div>
                <div class="team-grid">
                  ${teams.map((review) => {
                    const concern = (review.concerns || [])[0] || {};
                    const evidence = (concern.evidence || [])[0];
                    return `
                      <div class="team-card">
                        <div class="team-top">
                          <strong>${esc(titleTeam(review.team))}</strong>
                          <span class="readiness ${esc(review.readiness)}">${esc(review.readiness)}</span>
                        </div>
                        <div>${esc(concern.statement || 'No concern captured.')}</div>
                        <div class="evidence">${esc(concern.evidence_status || 'needs confirmation')} ${evidence ? `- ${esc(evidence.source_type)}/${esc(evidence.source_id)}: ${esc(evidence.excerpt)}` : '- no source yet'}</div>
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
              ${listBlock('Kickoff agenda', summary.kickoff_agenda)}
            </div>
          </div>
        `;
      }

      function botMessage(content, compact = false) {
        return `
          <article class="message ${compact ? 'compact' : ''}">
            <div class="avatar bot">PF</div>
            <div>
              <div class="meta"><span class="name">PreFlight</span><span class="time">now</span></div>
              ${content}
            </div>
          </article>
        `;
      }

      function pmMessage(content) {
        return `
          <article class="message">
            <div class="avatar pm">PM</div>
            <div>
              <div class="meta"><span class="name">Priya PM</span><span class="time">now</span></div>
              ${content}
            </div>
          </article>
        `;
      }

      function renderChoicePrompt() {
        state.active = null;
        clearTimers();
        els.currentReadiness.textContent = 'PICK ONE';
        els.currentReadiness.style.color = 'var(--accent)';
        els.currentBlockers.textContent = '-';
        els.composerText.textContent = 'Choose a kickoff brief above...';
        els.composerText.classList.remove('active');
        const options = state.scenarios.map((item, index) => {
          const [kicker, title, description, tone] = optionCopy(item.run || {});
          return `
            <button class="option-card" data-tone="${esc(tone)}" data-scenario="${index}">
              <span class="option-kicker">${esc(kicker)}</span>
              <strong>${esc(title)}</strong>
              <span>${esc(description)}</span>
            </button>
          `;
        }).join('');
        els.messages.innerHTML = `
          ${botMessage(`
            <div class="text">What are we preflighting?</div>
            <div class="option-grid">${options}</div>
          `)}
        `;
        document.querySelectorAll('[data-scenario]').forEach((button) => {
          button.addEventListener('click', () => startScenario(Number(button.dataset.scenario)));
        });
      }

      function clearTimers() {
        state.timers.forEach((timer) => window.clearTimeout(timer));
        state.timers = [];
      }

      function sourceSummary(run) {
        const seen = new Set();
        const refs = [];
        (run.team_reviews || []).forEach((review) => {
          (review.concerns || []).forEach((concern) => {
            (concern.evidence || []).forEach((evidence) => {
              const key = `${evidence.source_type}/${evidence.source_id}`;
              if (!seen.has(key)) {
                seen.add(key);
                refs.push(key);
              }
            });
          });
        });
        return refs.slice(0, 5);
      }

      function triageCard(lines, activeLine, sources = []) {
        const progress = Math.round((activeLine / Math.max(lines.length, 1)) * 100);
        return `
          <div class="triage">
            <div class="triage-top">
              <div class="triage-title">Source triage</div>
              <div class="triage-score">${progress}%</div>
            </div>
            <div class="triage-progress"><span style="width:${progress}%"></span></div>
            <div class="source-row">
              ${sources.slice(0, 5).map((source) => `<span class="source-chip">${esc(source)}</span>`).join('')}
            </div>
            ${lines.map((line, index) => `
              <div class="source-step">
                ${index < activeLine ? '<span class="check">✓</span>' : '<span class="pulse"></span>'}
                <span>${esc(line)}</span>
              </div>
            `).join('')}
          </div>
        `;
      }

      function schedule(delay, callback) {
        const timer = window.setTimeout(callback, delay);
        state.timers.push(timer);
      }

      function setWorkflowHtml(html) {
        els.messages.innerHTML = html;
        els.messages.closest('.conversation')?.scrollTo({ top: els.messages.scrollHeight, behavior: 'smooth' });
      }

      function startScenario(index) {
        const item = state.scenarios[index];
        if (!item) return;
        clearTimers();
        state.active = index;

        const run = item.run;
        const metrics = item.metrics || {};
        const readiness = run.moderator_summary?.overall_readiness || 'yellow';
        const sources = sourceSummary(run);
        const teams = (run.team_reviews || []).map((review) => titleTeam(review.team)).join(', ');
        const steps = [
          `Parsed brief and selected ${teams}`,
          `Checked ${sources.slice(0, 2).join(' + ') || 'seed context'}`,
          `Cross-read ${sources.slice(2, 5).join(' + ') || 'team policies'}`,
          'Synthesized blockers, owners, and agenda'
        ];

        els.currentReadiness.textContent = 'TRIAGING';
        els.currentReadiness.style.color = 'var(--accent)';
        els.currentBlockers.textContent = '-';
        els.composerText.textContent = 'PreFlight is triaging sources...';
        els.composerText.classList.add('active');

        const base = `
          ${pmMessage(`
            <div class="text">Can PreFlight check this before kickoff?</div>
            <pre class="brief">${esc(briefText(run))}</pre>
          `)}
          ${botMessage('<div class="text">On it. I’ll check the team lenses and source trail.</div>', true)}
        `;
        setWorkflowHtml(base + botMessage('<div class="typing"><span></span><span></span><span></span></div>', true));

        steps.forEach((_, stepIndex) => {
          schedule(650 + stepIndex * 650, () => {
            setWorkflowHtml(base + botMessage(triageCard(steps.slice(0, stepIndex + 1), stepIndex, sources), true));
          });
        });

        schedule(650 + steps.length * 650, () => {
          els.currentReadiness.textContent = readiness.toUpperCase();
          els.currentReadiness.style.color = readiness === 'red' ? 'var(--red)' : readiness === 'green' ? 'var(--green)' : 'var(--yellow)';
          els.currentBlockers.textContent = String(metrics.blocker_count ?? 0);
          els.composerText.textContent = 'Message #preflight-demo...';
          els.composerText.classList.remove('active');
          setWorkflowHtml(`
            ${base}
            ${botMessage(triageCard(steps, steps.length, sources), true)}
            ${botMessage('<div class="text">Done. Posting the thread.</div>', true)}
            ${botMessage(`
              <div class="text">PreFlight review complete.</div>
              ${renderReview(run)}
            `)}
            ${pmMessage('<div class="text">Perfect. I can schedule the kickoff with owners already named.</div>')}
          `);
        });
      }

      async function loadDemo() {
        const response = await fetch('/api/demo');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      }

      async function main() {
        try {
          const payload = await loadDemo();
          state.scenarios = payload.scenarios || [];
          els.scenarioCount.textContent = String(payload.scenario_count ?? state.scenarios.length);
          els.evidenceRatio.textContent = `${Math.round((payload.evidence_backed_ratio || 0) * 100)}%`;
          renderChoicePrompt();
          schedule(650, () => els.bootLoader?.classList.add('hidden'));
        } catch (error) {
          els.bootLoader?.classList.add('hidden');
          els.messages.innerHTML = `
            <article class="message">
              <div class="avatar bot">PF</div>
              <div>
                <div class="meta"><span class="name">PreFlight</span><span class="time">now</span></div>
                <div class="text">Demo data failed to load: ${esc(error.message)}</div>
              </div>
            </article>
          `;
        }

        els.resetDemo.addEventListener('click', renderChoicePrompt);
      }

      main();
    </script>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return demo()


@app.get("/history", response_class=HTMLResponse)
def history() -> str:
    return """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>PreFlight Dashboard</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
    <link href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap\" rel=\"stylesheet\" />
    <style>
      :root {
        --bg: radial-gradient(circle at 10% 10%, #ffe8ce, #f8f5ef 45%, #e5f4ef 100%);
        --text: #1d2a24;
        --muted: #5a6a64;
        --card: rgba(255, 255, 255, 0.8);
        --border: rgba(29, 42, 36, 0.12);
        --green: #0e7a43;
        --yellow: #a56a00;
        --red: #a11c1c;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: \"IBM Plex Sans\", -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text);
        background: var(--bg);
      }

      .page {
        max-width: 1260px;
        margin: 0 auto;
        padding: 24px 18px 40px;
      }

      .header {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 20px;
      }

      .title {
        font-size: clamp(1.6rem, 2.6vw, 2.2rem);
        font-weight: 700;
        margin: 0;
      }

      .subtitle {
        margin: 8px 0 0;
        color: var(--muted);
      }

      .chip {
        align-self: flex-start;
        font-family: \"IBM Plex Mono\", ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.8rem;
        padding: 8px 10px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid var(--border);
      }

      .panel {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 14px;
      }

      .cards {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 20px;
      }

      .card {
        background: var(--card);
        backdrop-filter: blur(6px);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px;
      }

      .label {
        color: var(--muted);
        font-size: 0.86rem;
        margin: 0 0 8px;
      }

      .value {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
      }

      .value.green { color: var(--green); }
      .value.yellow { color: var(--yellow); }
      .value.red { color: var(--red); }

      h2 {
        margin: 0 0 12px;
        font-size: 1rem;
      }

      .list {
        margin: 0;
        padding-left: 18px;
        display: grid;
        gap: 8px;
      }

      .filters {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr 1fr auto;
        gap: 10px;
      }

      .filters input,
      .filters select {
        width: 100%;
        border-radius: 10px;
        border: 1px solid var(--border);
        padding: 8px 10px;
        font: inherit;
      }

      .filters button {
        border-radius: 10px;
        border: 1px solid #203f34;
        background: #203f34;
        color: #fff;
        padding: 8px 12px;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
      }

      .filters .ghost {
        background: transparent;
        color: #203f34;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
      }

      th,
      td {
        text-align: left;
        padding: 9px 8px;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
      }

      th {
        font-weight: 600;
        color: var(--muted);
      }

      .badge {
        display: inline-block;
        font-size: 0.72rem;
        padding: 3px 8px;
        border-radius: 999px;
        border: 1px solid var(--border);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .badge.green { color: var(--green); border-color: rgba(14, 122, 67, 0.35); }
      .badge.yellow { color: var(--yellow); border-color: rgba(165, 106, 0, 0.35); }
      .badge.red { color: var(--red); border-color: rgba(161, 28, 28, 0.35); }

      .muted { color: var(--muted); }
      code { font-family: \"IBM Plex Mono\", ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; }

      @media (max-width: 950px) {
        .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }

      @media (max-width: 640px) {
        .cards { grid-template-columns: 1fr; }
        .filters { grid-template-columns: 1fr; }
        th:nth-child(4), td:nth-child(4), th:nth-child(7), td:nth-child(7) { display: none; }
      }
    </style>
  </head>
  <body>
    <main class=\"page\">
      <section class=\"header\">
        <div>
          <h1 class=\"title\">PreFlight Run Dashboard</h1>
          <p class=\"subtitle\">Run history, readiness posture, and fast drilldown into concerns and evidence.</p>
        </div>
        <div class=\"chip\" id=\"lastUpdated\">Loading...</div>
      </section>

      <section class=\"panel\">
        <h2>Filters</h2>
        <form class=\"filters\" id=\"filterForm\">
          <input id=\"initiativeContains\" placeholder=\"Search initiative title\" />
          <select id=\"readiness\">
            <option value=\"\">Any readiness</option>
            <option value=\"green\">Green</option>
            <option value=\"yellow\">Yellow</option>
            <option value=\"red\">Red</option>
          </select>
          <input id=\"team\" placeholder=\"Team (engineering, qa, tpm...)\" />
          <input id=\"requester\" placeholder=\"Requester\" />
          <div style=\"display:flex; gap:8px;\">
            <button type=\"submit\">Apply</button>
            <button type=\"button\" class=\"ghost\" id=\"clearFilters\">Clear</button>
          </div>
        </form>
      </section>

      <section class=\"cards\">
        <article class=\"card\"><p class=\"label\">Total Runs</p><p class=\"value\" id=\"totalRuns\">-</p></article>
        <article class=\"card\"><p class=\"label\">Green</p><p class=\"value green\" id=\"greenRuns\">-</p></article>
        <article class=\"card\"><p class=\"label\">Yellow</p><p class=\"value yellow\" id=\"yellowRuns\">-</p></article>
        <article class=\"card\"><p class=\"label\">Red</p><p class=\"value red\" id=\"redRuns\">-</p></article>
      </section>

      <section class=\"panel\">
        <h2>Top Blockers</h2>
        <ol class=\"list\" id=\"topBlockers\"></ol>
      </section>

      <section class=\"panel\">
        <h2>Recent Runs</h2>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Initiative</th>
              <th>Requester</th>
              <th>Readiness</th>
              <th>Teams</th>
              <th>Blockers</th>
              <th>Slack</th>
            </tr>
          </thead>
          <tbody id=\"runRows\"></tbody>
        </table>
      </section>
    </main>

    <script>
      const els = {
        totalRuns: document.getElementById('totalRuns'),
        greenRuns: document.getElementById('greenRuns'),
        yellowRuns: document.getElementById('yellowRuns'),
        redRuns: document.getElementById('redRuns'),
        topBlockers: document.getElementById('topBlockers'),
        runRows: document.getElementById('runRows'),
        lastUpdated: document.getElementById('lastUpdated'),
        filterForm: document.getElementById('filterForm'),
        readiness: document.getElementById('readiness'),
        team: document.getElementById('team'),
        requester: document.getElementById('requester'),
        initiativeContains: document.getElementById('initiativeContains'),
        clearFilters: document.getElementById('clearFilters'),
      };

      function readinessBadge(readiness) {
        const r = (readiness || '').toLowerCase();
        return `<span class=\"badge ${r}\">${r || 'unknown'}</span>`;
      }

      function relativeIso(iso) {
        try { return new Date(iso).toLocaleString(); } catch (_) { return iso; }
      }

      function readFiltersFromUrl() {
        const params = new URLSearchParams(window.location.search);
        return {
          readiness: params.get('readiness') || '',
          team: params.get('team') || '',
          requester: params.get('requester') || '',
          initiative_contains: params.get('initiative_contains') || '',
        };
      }

      function writeFiltersToInputs(filters) {
        els.readiness.value = filters.readiness;
        els.team.value = filters.team;
        els.requester.value = filters.requester;
        els.initiativeContains.value = filters.initiative_contains;
      }

      function writeFiltersToUrl(filters) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
          if (value) params.set(key, value);
        });
        const query = params.toString();
        const next = query ? `${window.location.pathname}?${query}` : window.location.pathname;
        history.replaceState({}, '', next);
      }

      function currentFiltersFromInputs() {
        return {
          readiness: els.readiness.value.trim(),
          team: els.team.value.trim(),
          requester: els.requester.value.trim(),
          initiative_contains: els.initiativeContains.value.trim(),
        };
      }

      function slackQuickLink(run) {
        if (!run.channel_id) return '<span class=\"muted\">n/a</span>';
        const channel = encodeURIComponent(run.channel_id);
        const link = `https://slack.com/app_redirect?channel=${channel}`;
        return `<a href=\"${link}\" target=\"_blank\" rel=\"noreferrer\">open</a>`;
      }

      async function loadData(filters) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
          if (value) params.set(key, value);
        });
        const response = await fetch(`/api/dashboard?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      }

      function render(payload) {
        const dash = payload.dashboard || {};
        const readiness = dash.readiness || {};
        const runs = (payload.runs && payload.runs.runs) || [];

        els.totalRuns.textContent = String(dash.total_runs ?? 0);
        els.greenRuns.textContent = String(readiness.green ?? 0);
        els.yellowRuns.textContent = String(readiness.yellow ?? 0);
        els.redRuns.textContent = String(readiness.red ?? 0);

        const blockers = dash.top_blockers || [];
        els.topBlockers.innerHTML = blockers.length
          ? blockers.map((b) => `<li>${b}</li>`).join('')
          : '<li class=\"muted\">No blockers recorded yet.</li>';

        els.runRows.innerHTML = runs.length
          ? runs.map((run) => `
              <tr>
                <td>
                  <a href=\"/run/${run.run_id}\"><code>${run.run_id}</code></a><br/>
                  <span class=\"muted\">${relativeIso(run.created_at)}</span>
                </td>
                <td>${run.initiative_title}</td>
                <td>${run.requester || '<span class=\"muted\">n/a</span>'}</td>
                <td>${readinessBadge(run.overall_readiness)}</td>
                <td>${(run.teams || []).join(', ') || '<span class=\"muted\">n/a</span>'}</td>
                <td>${run.blocker_count ?? 0}</td>
                <td>${slackQuickLink(run)}</td>
              </tr>
            `).join('')
          : '<tr><td colspan=\"7\" class=\"muted\">No runs available for the selected filters.</td></tr>';

        els.lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString()}`;
      }

      async function refresh(filters) {
        const data = await loadData(filters);
        render(data);
      }

      async function main() {
        const urlFilters = readFiltersFromUrl();
        writeFiltersToInputs(urlFilters);

        try {
          await refresh(urlFilters);
        } catch (error) {
          els.lastUpdated.textContent = `Error: ${error.message}`;
          els.topBlockers.innerHTML = '<li class=\"muted\">Dashboard data unavailable.</li>';
          els.runRows.innerHTML = '<tr><td colspan=\"7\" class=\"muted\">Unable to load run history from orchestrator.</td></tr>';
        }

        els.filterForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          const filters = currentFiltersFromInputs();
          writeFiltersToUrl(filters);
          await refresh(filters);
        });

        els.clearFilters.addEventListener('click', async () => {
          const filters = {
            readiness: '',
            team: '',
            requester: '',
            initiative_contains: '',
          };
          writeFiltersToInputs(filters);
          writeFiltersToUrl(filters);
          await refresh(filters);
        });
      }

      main();
      setInterval(() => {
        const filters = readFiltersFromUrl();
        refresh(filters).catch(() => undefined);
      }, 20000);
    </script>
  </body>
</html>
"""


@app.get("/run/{run_id}", response_class=HTMLResponse)
def run_detail(run_id: str) -> str:
    html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PreFlight Run __RUN_ID_TEXT__</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet" />
    <style>
      :root {
        --bg: linear-gradient(130deg, #f7f8ef, #ecf7f3 60%, #f9efe5);
        --text: #1d2a24;
        --muted: #5a6a64;
        --card: rgba(255, 255, 255, 0.88);
        --border: rgba(29, 42, 36, 0.14);
      }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: "IBM Plex Sans", -apple-system, sans-serif; background: var(--bg); color: var(--text); }
      .page { max-width: 1080px; margin: 0 auto; padding: 24px 18px 40px; }
      .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-bottom: 14px; }
      h1 { margin: 0 0 8px; font-size: 1.5rem; }
      .muted { color: var(--muted); }
      .meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
      .meta-item { border: 1px solid var(--border); border-radius: 10px; padding: 10px; }
      .team { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); }
      ul { margin: 8px 0; padding-left: 18px; }
      code { font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.83rem; }
      a { color: #234f62; }
      @media (max-width: 780px) { .meta { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <main class="page">
      <div class="card">
        <p><a href="/">Back to demo</a></p>
        <h1 id="title">Run __RUN_ID_TEXT__</h1>
        <p class="muted" id="summary">Loading run detail...</p>
        <div class="meta" id="meta"></div>
      </div>
      <div class="card">
        <h2>Moderator Synthesis</h2>
        <div id="moderator" class="muted">Loading...</div>
      </div>
      <div class="card">
        <h2>Team Concerns and Evidence</h2>
        <div id="teams" class="muted">Loading...</div>
      </div>
    </main>

    <script>
      const runId = __RUN_ID_JSON__;

      async function loadRun() {
        const response = await fetch(`/api/runs/${runId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      }

      function list(values) {
        if (!values || values.length === 0) return '<span class="muted">none</span>';
        return `<ul>${values.map((v) => `<li>${v}</li>`).join('')}</ul>`;
      }

      function render(run) {
        document.getElementById('title').textContent = `${run.initiative_title}`;
        document.getElementById('summary').textContent = `Run ${run.run_id} • ${new Date(run.created_at).toLocaleString()}`;
        document.getElementById('meta').innerHTML = `
          <div class="meta-item"><strong>Requester</strong><div>${run.requester || '<span class=\"muted\">n/a</span>'}</div></div>
          <div class="meta-item"><strong>Channel</strong><div>${run.channel_id || '<span class=\"muted\">n/a</span>'}</div></div>
          <div class="meta-item"><strong>Thread</strong><div>${run.thread_ts || '<span class=\"muted\">n/a</span>'}</div></div>
        `;

        const moderator = run.moderator_summary || {};
        document.getElementById('moderator').innerHTML = `
          <p><strong>Overall readiness:</strong> ${moderator.overall_readiness || 'n/a'}</p>
          <p><strong>Blockers</strong>${list(moderator.blockers)}</p>
          <p><strong>Dependencies</strong>${list(moderator.dependencies)}</p>
          <p><strong>Questions to resolve</strong>${list(moderator.questions_to_resolve)}</p>
          <p><strong>Suggested owners</strong>${list(moderator.suggested_owners)}</p>
          <p><strong>Kickoff agenda</strong>${list(moderator.kickoff_agenda)}</p>
          <p><strong>Warnings</strong>${list(moderator.warnings)}</p>
        `;

        const teams = run.team_reviews || [];
        document.getElementById('teams').innerHTML = teams.length
          ? teams.map((review) => `
              <div class="team">
                <p><strong>${review.team}</strong> • ${review.readiness}</p>
                ${(review.concerns || []).map((concern) => `
                  <div style="margin-bottom:12px;">
                    <p><strong>Concern:</strong> ${concern.statement}</p>
                    <p><strong>Confidence:</strong> ${concern.confidence} • <strong>Evidence status:</strong> ${concern.evidence_status}</p>
                    <p><strong>Blockers</strong>${list(concern.blockers)}</p>
                    <p><strong>Questions</strong>${list(concern.questions)}</p>
                    <p><strong>Evidence</strong>${(concern.evidence || []).length ? `<ul>${concern.evidence.map((e) => `<li><code>${e.source_type}/${e.source_id}</code> — ${e.excerpt}</li>`).join('')}</ul>` : '<span class=\"muted\">none</span>'}</p>
                  </div>
                `).join('')}
              </div>
            `).join('')
          : '<span class="muted">No team reviews found.</span>';
      }

      async function main() {
        try {
          const run = await loadRun();
          render(run);
        } catch (error) {
          document.getElementById('summary').textContent = `Failed to load run detail: ${error.message}`;
          document.getElementById('moderator').textContent = 'Unavailable';
          document.getElementById('teams').textContent = 'Unavailable';
        }
      }

      main();
    </script>
  </body>
</html>
"""
    return html.replace("__RUN_ID_JSON__", json.dumps(run_id)).replace("__RUN_ID_TEXT__", run_id)
