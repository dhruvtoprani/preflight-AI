from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _history_auth_token() -> str:
    return os.getenv("PREFLIGHT_HISTORY_API_TOKEN", "").strip()

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="PreFlight Dashboard", version="0.1.0")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
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
        <p><a href="/">Back to dashboard</a></p>
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
