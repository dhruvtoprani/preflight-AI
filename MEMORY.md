# PreFlight Memory Log

Last Updated: 2026-05-18
Project Path: `/Users/dhruvtoprani/Desktop/Projects/preflight-AI`

## 1) Keep Forever (High-Signal Context)

### Product Identity
- Name: **PreFlight**
- Framing: **Slack-native stakeholder context engine for PMs and TPMs**
- Avoid framing: "digital twins of employees"
- Value prop: pre-meeting alignment intelligence

### One-Liner
- PreFlight helps PMs and TPMs pressure-test initiatives before kickoff by running async, role-based AI reviews grounded in internal context.

### Non-Negotiable Build Rule (from user)
- Every MVP must be iteratively useful and scalable.
- No throwaway code that cannot be leveraged later.

### Core Product Decisions (Locked)
1. Primary UX is Slack-threaded multi-agent review.
2. MVP starts with seeded docs/exports, then live integrations.
3. Agent-scoped retrieval (no giant shared context window).
4. Every concern includes:
   - `evidence-backed | inferred | needs confirmation`
   - confidence score
   - source references

## 2) Current Architecture Snapshot
- `apps/slack-bot`: Slack interaction and transport
- `services/orchestrator`: review workflow and synthesis
- `services/ingestion`: parsing/chunking/indexing pipeline
- `services/retrieval`: team-scoped context access
- `packages/schemas`: shared contracts (Pydantic)
- `packages/agent-prompts`: role prompts
- `packages/shared-utils`: common helpers
- `infra`: Postgres+pgvector, Redis, migrations

## 3) Current Build State
### Completed
1. Project scope draft: `PRE_FLIGHT_PROJECT_SCOPE.md`
2. PRD draft: `PRE_FLIGHT_PRD_DRAFT.md`
3. Monorepo scaffold and base docs/configs
4. Schema package v0.1
5. Orchestrator service stub (`/health`, `/review`)
6. Slack bot service stub (`/health`, `/config-check`)
7. Ingestion and retrieval placeholders
8. Python syntax validation passed (`checked=14`, `syntax_ok`)

### In Progress
- Transitioning from scaffold to first end-to-end MVP path.

## 4) Operational Backlog (Source of Truth)
Canonical backlog: `docs/ACTION_ITEMS.md`

Execution order currently intended:
1. Contract tests + payload fixtures
2. Orchestrator runner abstraction + scoring rubric
3. Slack intake wiring to orchestrator
4. Seeded ingestion + retrieval pipeline v0
5. Observability + graceful partial-failure handling

## 5) Open Decisions (Need Founder Input)
1. Slack-only MVP vs Slack + minimal dashboard in first cut
2. Readiness scoring output format:
   - color only
   - color + numeric score
3. First live integration priority after seeded docs:
   - Jira first
   - Confluence first

## 6) Journal (Append-Only)

### 2026-05-18 - Repo Scaffold Initialized
- Created production-shaped monorepo directories and service/package boundaries.
- Added root configs (`.gitignore`, `.editorconfig`, `.env.example`) and root `README.md`.
- Added `docs/ACTION_ITEMS.md`, `docs/ARCHITECTURE.md`, `docs/ADR-0001-repo-structure.md`.
- Added shared schema models for initiative/review/evidence/readiness.
- Added orchestrator, Slack app, ingestion, retrieval service stubs.
- Added local infra bootstrap (`infra/docker-compose.yml`, `scripts/dev-up.sh`).

Why:
- Ensure MVP implementation is directly extensible and non-throwaway.

Impact:
- Repo is build-ready for first integrated vertical slice.

### 2026-05-18 - Scaffold Validation
- Ran syntax checks across Python files.
- Result: clean parse across all current modules.

Why:
- Establish stable baseline before feature wiring.

Impact:
- Safe to proceed with implementation tasks.

## 7) Journal Rules
For each significant change, append:
1. What changed
2. Why
3. Impact
4. New action items (if any)

Keep entries concise and operational.

### 2026-05-18 - Memory and Backlog Curation
- Refactored `MEMORY.md` into high-signal operational format.
- Removed low-value repetition and centralized backlog authority to `docs/ACTION_ITEMS.md`.
- Rewrote action items into three execution batches with acceptance criteria.

Why:
- Keep context durable and scannable as chat history grows.
- Make approval and execution sequencing explicit before further coding.

Impact:
- Faster future session recovery.
- Clear greenlight gates for implementation phases.

### 2026-05-18 - Batch A Implemented (Foundation Hardening)
- Added root `Makefile` with standardized local commands (`lint`, `test`, `run-orchestrator`, `run-slack`, `dev-up`).
- Added `scripts/check_syntax.py` for dependency-free lint/syntax verification.
- Added contract tests and fixtures for initiative intake and review evidence status validation.
- Added deterministic readiness scoring spec: `docs/SCORING_SPEC.md`.
- Introduced orchestrator pluggable runner interface:
  - `AgentRunner` protocol
  - `DeterministicRunner` default implementation
- Refactored `engine.py` to use runner injection + moderator summary aggregation + scoring module.

Why:
- Complete Batch A with production-shaped, test-backed foundations.

Impact:
- Contracts are now test-enforced.
- Scoring is deterministic and documented.
- Orchestrator can evolve to live agent execution without architectural rewrite.

Validation:
- `make lint` passed (`syntax_ok files=23`).
- `make test` passed (`Ran 9 tests ... OK`).

New action item discovered and resolved during execution:
- Resolved Python module shadowing by renaming test directory from `tests/orchestrator` to `tests/orchestration`.

### 2026-05-18 - Batch B Implemented (First Vertical Slice)
- Implemented Slack intake endpoint flow in `apps/slack-bot`:
  - `POST /intake` receives `InitiativeBrief`
  - calls orchestrator `/review`
  - formats thread-style output preview
  - persists run with JSON fallback store
- Added `call_orchestrator_review` in slack app using stdlib HTTP transport.
- Added thread formatter module for moderator + team perspective rendering.
- Added `ReviewRunStore` persistence stub with file fallback (`data/review_runs` or `PREFLIGHT_RUN_DIR`).
- Added orchestrator partial-failure support:
  - `RunnerResult` contract (`team_reviews`, `warnings`)
  - deterministic runner supports `timeout_team` simulation
  - warning propagation into `ModeratorSummary.warnings`
- Extended orchestrator `/review` endpoint with `timeout_team` query handling.

Why:
- Complete first end-to-end vertical slice from intake to structured review output.
- Ensure graceful degradation when one agent fails/times out.

Impact:
- System now produces a practical review artifact even with partial agent failures.
- Slack-facing integration path is in place for real Bolt wiring next.

Validation:
- `make lint` passed (`syntax_ok files=31`).
- `make test` passed (`Ran 12 tests ... OK`).
- Added tests for:
  - runner timeout partial results
  - warning propagation
  - formatter output structure
  - intake -> orchestrator -> persistence flow

Notable execution adjustment:
- Replaced `httpx` requirement in slack intake path with stdlib HTTP to keep runtime/test environment dependency-light.

### 2026-05-18 - Batch C Implemented (Dump-First Retrieval + Evidence Quality)
- Implemented connector-ready dump ingestion path:
  - Added `SourceConnector` protocol and `SeedDumpConnector` in `services/ingestion`.
  - Added `ingest_seed_documents` to normalize JSON exports into JSONL index format.
- Implemented team-scoped retrieval path:
  - Added `SourceDocument` and `RetrievedSnippet` schemas.
  - Added lexical retrieval with team visibility scoping and source tagging.
- Added evidence quality enforcement:
  - `Concern` model validator now requires evidence references when status is `evidence-backed`.
- Added observability:
  - `ReviewObservabilityEvent` schema.
  - `JsonlObservabilitySink` + event builder.
  - `run_preflight` now emits observability event per run.
- Added tests:
  - ingestion pipeline test
  - retrieval scoping test
  - evidence enforcement contract test
  - observability emission test

Why:
- Deliver real retrieval and trust foundations while keeping architecture ready for later clean Jira/Confluence pulls.

Impact:
- Batch C acceptance criteria are met with passing tests.
- Data path now supports exported-dump ingestion today and connector upgrades later.

Notable execution adjustments:
1. Renamed test directories to avoid module shadowing collisions.
2. Moved default event/run persistence to temp-safe writable paths for reliable local/test execution.

Validation:
- `make lint` passed (`syntax_ok files=39`).
- `make test` passed (`Ran 16 tests ... OK`).

Next queued batch:
- Batch D: live Jira/Confluence connectors with incremental sync checkpoints.

### 2026-05-18 - LLM-Driven Team Runner + Prompt/Policy Layer
- Added LLM review path in orchestrator with automatic mode selection:
  - `PREFLIGHT_RUNNER_MODE=auto|llm|deterministic`
  - `auto` uses LLM when `OPENAI_API_KEY` exists, otherwise deterministic fallback
- Added `OpenAIChatClient` adapter and response parsing pipeline.
- Added configurable per-team documentation access policies:
  - file: `services/orchestrator/config/team_context_policies.json`
  - includes focus areas, preferred sources, retrieval hints per team
- Added prompt repository and structured team prompt builder with explicit slots for:
  - initiative needs and expectations
  - team availability/capacity risk
  - allowed source types (Confluence/Jira/Drive/etc.)
  - retrieved context snippets
- Added templates for all core teams:
  - engineering, qa, design, support, gtm, security_privacy, tpm (+ general fallback)
- Added concern validation hardening and fallback behavior for malformed model outputs.

Why:
- Shift from hardcoded deterministic reviews to configurable LLM-driven team analysis while preserving reliability and future connector flexibility.

Impact:
- Product can now produce team reviews via LLM with role prompts and source-scoping instructions.
- Dump-based retrieval stays compatible and ready for clean Jira/Confluence connector replacement later.

Validation:
- `make lint` passed (`syntax_ok files=44`).
- `make test` passed (`Ran 18 tests ... OK`).

### 2026-05-18 - Batch E Implemented (Live Connectors + Health Expansion)
- Added live connector implementations:
  - `JiraConnector` with pagination, JQL filtering, normalization, and team-scope inference from labels.
  - `ConfluenceConnector` with pagination, page normalization, HTML stripping, and team-scope inference from labels/text.
- Added incremental sync infrastructure:
  - `CheckpointStore` for per-connector watermark persistence.
  - `sync_live_sources` for deduping merge-write into normalized index.
  - CLI entrypoint: `scripts/sync_live_sources.py` and `make sync-live`.
- Added richer service health checks:
  - Orchestrator `/health/full` now reports runner/config/index/connector readiness.
  - Slack-bot `/health/full` now verifies orchestrator reachability plus token/config readiness.
- Expanded env configuration with Jira/Confluence credentials and connector tuning variables.
- Added tests for:
  - Jira pagination and scope extraction
  - Confluence since-cursor filtering
  - live sync merge + checkpoint behavior
  - health payload completeness

Why:
- Move from dump-only ingestion toward clean live source pulls while preserving existing retrieval/orchestration contracts.
- Provide runtime health visibility for multi-service reliability checks.

Impact:
- System supports connector-based ingestion with incremental sync.
- Health endpoints are now meaningful enough for deploy-time uptime checks.

Validation:
- `make lint` passed (`syntax_ok files=51`).
- `make test` passed (`Ran 22 tests ... OK`).

### 2026-05-18 - Post-Interrupt Completion + Health Smoke
- Completed pending connector/sync/health test suite work after interrupted turn.
- Added tests for live connectors, incremental sync checkpoints, and health payload checks.
- Fixed default team policy path bug (`services/orchestrator/config/...`) used by `/health/full`.
- Added slack-bot `/health/full` endpoint for orchestrator linkage checks.
- Added runbook doc: `docs/HEALTHCHECK_RUNBOOK.md`.
- Ran local smoke test and confirmed:
  - `http://127.0.0.1:8000/health/full` responds
  - `http://127.0.0.1:8001/health/full` responds

Validation:
- `make lint` passed (`syntax_ok files=51`).
- `make test` passed (`Ran 22 tests ... OK`).

### 2026-05-18 - Orchestration Wiring Upgrade (Coding Focus)
- Upgraded `LLMTeamRunner` to run team reviews in parallel using a thread pool.
- Added orchestrated timeout handling:
  - global review timeout guard
  - per-team fallback review when timeout/failure occurs
  - warning propagation to moderator summary
- Added model resilience behavior:
  - LLM retry loop (`PREFLIGHT_LLM_RETRIES`)
  - guarded concern parsing with fallback/downgrade behavior
- Added orchestrator pipeline hooks:
  - `POST /sync` endpoint for live connector sync
  - `sync_before_review` option on `POST /review`
  - sync warnings appended into review warnings
- Added env controls for orchestration:
  - `PREFLIGHT_MAX_PARALLEL_AGENTS`
  - `PREFLIGHT_REVIEW_TIMEOUT_SECONDS`
  - `PREFLIGHT_LLM_RETRIES`
- Added tests:
  - timeout fallback in LLM runner
  - sync-warning propagation through review path

Validation:
- `make lint` passed (`syntax_ok files=52`).
- `make test` passed (`Ran 24 tests ... OK`).

### 2026-05-18 - Batch G Implemented (Slack Hookup)
- Added Slack-oriented service modules:
  - `slack_client.py` for outbound thread messaging
  - `idempotency.py` for duplicate suppression
  - `service.py` for run workflow + notify orchestration
- Added Slack endpoints in FastAPI app:
  - `POST /slack/command`
  - `POST /slack/events`
- Added async background review execution flow with thread progress/final messages.
- Added idempotency keying based on channel/thread/requester/payload hash.
- Added env-gated controls for async and sync-before-review behavior.
- Updated intake/orchestrator call path to support `sync_before_review` flag propagation.
- Added Slack test coverage for:
  - idempotency duplicate detection
  - command route acceptance and sync flag query propagation
  - service duplicate handling

Notable adjustment:
- Changed Slack SDK import to lazy runtime import so non-Slack test environments remain runnable.

Validation:
- `make lint` passed (`syntax_ok files=58`).
- `make test` passed (`Ran 28 tests ... OK`).

### 2026-05-18 - Batch H Completed (Moderator LLM Synthesis)
- Added moderator synthesis module:
  - `services/orchestrator/src/orchestrator/moderator.py`
  - Includes `ModeratorConfig`, `Moderator` protocol, `DeterministicModerator`, `LLMModerator`, and `build_default_moderator()`.
- Refactored orchestration engine to consume pluggable moderator layer:
  - Updated `services/orchestrator/src/orchestrator/engine.py`
  - `run_preflight(...)` now accepts optional `moderator` and defaults via `build_default_moderator()`.
- Added moderator config env vars to `.env.example`:
  - `PREFLIGHT_MODERATOR_MODE=auto|llm|deterministic`
  - `PREFLIGHT_MODERATOR_MAX_BLOCKERS`
  - `PREFLIGHT_MODERATOR_MAX_DEPENDENCIES`
  - `PREFLIGHT_MODERATOR_MAX_QUESTIONS`
  - `PREFLIGHT_MODERATOR_MAX_OWNERS`
  - `PREFLIGHT_MODERATOR_MAX_AGENDA_ITEMS`
- Hardened test determinism in `tests/bootstrap.py`:
  - default `PREFLIGHT_RUNNER_MODE=deterministic`
  - default `PREFLIGHT_MODERATOR_MODE=deterministic`
- Expanded orchestration test coverage:
  - Updated `tests/orchestration/test_engine.py` to verify injected moderator usage.
  - Added `tests/orchestration/test_moderator.py` for:
    - LLM synthesis list normalization/caps
    - invalid JSON fallback to deterministic synthesis
    - default moderator selection when LLM mode requested without API key
- Updated `docs/ACTION_ITEMS.md`:
  - Marked Batch H complete.
  - Verification updated to current counts.

Validation:
- `make lint` passed (`syntax_ok files=60`).
- `make test` passed (`Ran 32 tests ... OK`).

### 2026-05-18 - Batch I Completed (Run Persistence + Queryability)
- Implemented shared run persistence and query layer:
  - Added `packages/shared-utils/src/shared_utils/run_store.py`
  - `ReviewRunStore` now supports:
    - Postgres-first persistence when `DATABASE_URL` points to postgres and `psycopg` is available
    - automatic file fallback persistence when Postgres is unavailable
    - run lookup (`get_run`)
    - history pagination/filtering (`history`)
    - dashboard summary aggregation (`dashboard`)
- Replaced Slack persistence stub:
  - `apps/slack-bot/src/slack_bot/persistence.py` now reuses shared `ReviewRunStore`
- Enriched core schemas for persistence/query use cases:
  - Updated `ReviewRun` in `packages/schemas/src/preflight_schemas/review.py` with:
    - `created_at`
    - `requester`
    - `channel_id`
    - `thread_ts`
  - Added history/dashboard API schema contracts in:
    - `packages/schemas/src/preflight_schemas/history.py`
  - Updated schema exports in:
    - `packages/schemas/src/preflight_schemas/__init__.py`
- Wired orchestrator persistence + query endpoints:
  - Updated `services/orchestrator/src/orchestrator/main.py`
  - `POST /review` now persists every run
  - Added `GET /runs` (pagination + filters)
  - Added `GET /runs/{run_id}`
  - Added `GET /runs/dashboard`
- Updated orchestration run generation metadata:
  - `services/orchestrator/src/orchestrator/engine.py` now carries requester/channel/thread into `ReviewRun`
- Updated test determinism/config:
  - `tests/bootstrap.py` sets default `DATABASE_URL=""` for offline deterministic tests
- Added Batch I test coverage:
  - New file: `tests/orchestration/test_run_history.py`
  - Verifies persistence-backed history, filtering, run lookup, and dashboard contract outputs
- Updated env documentation:
  - `.env.example` now documents Postgres activation and file fallback run directory (`PREFLIGHT_RUN_DIR`)
- Updated planning docs:
  - `docs/ACTION_ITEMS.md` marks Batch I complete and proposes Batch J

Validation:
- `make lint` passed (`syntax_ok files=63`).
- `make test` passed (`Ran 34 tests ... OK`).

### 2026-05-18 - Batch J Completed (Persistence Hardening + Dashboard Consumer)
- Added persistence hardening in shared run store:
  - Updated `packages/shared-utils/src/shared_utils/run_store.py`
  - New capabilities:
    - `persistence_diagnostics(check_connection=...)`
    - file fallback retention cleanup (`prune_file_fallback()`)
    - DB connect timeout config support
    - run-dir writability diagnostics
  - Retention envs:
    - `PREFLIGHT_RUN_FILE_RETENTION_DAYS`
    - `PREFLIGHT_RUN_FILE_MAX_FILES`
  - DB timeout env:
    - `PREFLIGHT_DB_CONNECT_TIMEOUT_SECONDS`
- Added startup + health diagnostics for persistence in orchestrator:
  - Updated `services/orchestrator/src/orchestrator/main.py`
    - startup log emits persistence diagnostics (`PREFLIGHT_PERSISTENCE_STARTUP_DB_CHECK` optional DB probe)
  - Updated `services/orchestrator/src/orchestrator/health.py`
    - `/health/full` now includes persistence diagnostics block and summary check status
    - optional DB check via `PREFLIGHT_PERSISTENCE_HEALTH_DB_CHECK`
- Added minimal dashboard consumer app:
  - New package `apps/dashboard`
  - New service file `apps/dashboard/src/dashboard_app/main.py`
    - `GET /health`
    - `GET /health/full`
    - `GET /api/dashboard` (aggregates orchestrator `/runs` and `/runs/dashboard`)
    - `GET /` (responsive HTML dashboard shell)
  - Added package config:
    - `apps/dashboard/pyproject.toml`
    - `apps/dashboard/src/dashboard_app/__init__.py`
- Unified runtime/test wiring for dashboard module:
  - Updated `Makefile`
    - added dashboard source path to PYTHONPATH
    - added `make run-dashboard`
  - Updated `tests/bootstrap.py`
    - added dashboard source path
- Updated docs/envs:
  - `.env.example` with new persistence retention + diagnostics toggles
  - `README.md` local run section includes dashboard
  - `docs/HEALTHCHECK_RUNBOOK.md` includes dashboard + persistence diagnostics
  - `docs/ACTION_ITEMS.md` marks Batch J complete and queues Batch K
- Added/updated tests:
  - `tests/shared/test_run_store.py`
    - retention cleanup behavior
    - Postgres driver-gap fallback behavior
    - persistence diagnostics reporting
  - `tests/dashboard/test_dashboard_main.py`
    - dashboard API aggregation behavior
    - HTML shell rendering check
  - `tests/orchestration/test_health.py`
    - persistence checks present in health payload

Validation:
- `make lint` passed (`syntax_ok files=69`).
- `make test` passed (`Ran 39 tests ... OK`).

### 2026-05-18 - Batch K Completed (Dashboard UX + Run Drilldown)
- Upgraded dashboard app for drilldown workflow and filter UX:
  - Updated `apps/dashboard/src/dashboard_app/main.py`
  - Added `GET /api/runs/{run_id}` dashboard passthrough to orchestrator run detail contract
  - Added `GET /run/{run_id}` detail page with:
    - moderator synthesis sections
    - per-team concern breakdown
    - evidence excerpt rendering
  - Enhanced `GET /` dashboard page with:
    - filter controls (`readiness`, `team`, `requester`, `initiative_contains`)
    - URL query-state sync via `history.replaceState`
    - quick links to run drilldown pages
    - Slack quick-link from channel metadata
- Fixed template rendering stability:
  - Replaced fragile f-string-based drilldown HTML with placeholder-based templating to avoid brace-escaping syntax errors in embedded JS/CSS.
- Added dashboard drilldown test coverage:
  - Updated `tests/dashboard/test_dashboard_main.py`
  - Added assertions for:
    - run-detail API passthrough
    - run-detail HTML shell rendering
    - filter-capable dashboard shell rendering

Validation:
- `make lint` passed (`syntax_ok files=69`).
- `make test` passed (`Ran 41 tests ... OK`).

### 2026-05-18 - Batch L Completed (Postgres Productionization + Access Control)
- Implemented minimal productionization/security layer with only essential code paths:
  - Updated orchestrator run-history APIs in `services/orchestrator/src/orchestrator/main.py`:
    - token auth boundary on `GET /runs`, `GET /runs/{run_id}`, `GET /runs/dashboard`
    - env: `PREFLIGHT_HISTORY_API_TOKEN`
    - default-safe redaction behavior for history payloads
    - optional sensitive output via `include_sensitive=true`
  - Added redaction helpers for common PII patterns (email/phone/Slack-like IDs).
- Added explicit Postgres dependency wiring:
  - `requirements.txt` now includes `psycopg[binary]>=3.2.0`
  - `services/orchestrator/pyproject.toml` includes `psycopg[binary]>=3.2.0`
- Added local DB/bootstrap validation command:
  - New script: `scripts/check_persistence_stack.py`
  - New Make target: `make check-persistence`
  - Supports strict-mode failure with `PREFLIGHT_PERSISTENCE_STRICT=true`
- Updated dashboard client to interoperate with protected run-history APIs:
  - `apps/dashboard/src/dashboard_app/main.py` forwards `Authorization: Bearer <PREFLIGHT_HISTORY_API_TOKEN>` when configured.
- Updated tests:
  - Added `tests/orchestration/test_history_security.py`
    - auth required/invalid/valid paths
    - redaction default behavior + include_sensitive override
  - Updated `tests/orchestration/test_run_history.py` to explicitly request sensitive detail where needed.
- Updated docs/config:
  - `.env.example` with auth + strict-check toggles
  - `README.md` with security defaults and persistence check command
  - `docs/ACTION_ITEMS.md` marks Batch L complete

Validation:
- `make lint` passed (`syntax_ok files=70`).
- `make test` passed (`Ran 43 tests ... OK`).

### 2026-05-18 - Batch M Completed (Pilot Delivery Cut)
- Added strict structured Slack intake parsing for higher-signal pilot submissions:
  - Updated `apps/slack-bot/src/slack_bot/main.py`
  - New behavior:
    - requires structured key:value brief fields
    - returns `status=needs_input` with template guidance when fields are missing/invalid
    - removes ad-hoc inferred brief creation from unstructured text
- Added one-command local stack launcher:
  - New script: `scripts/run_local_stack.sh`
  - Starts orchestrator (8000), slack-bot (8001), dashboard (8002)
  - Added make target: `run-local-stack`
- Added one-command pilot seed ingestion:
  - New script: `scripts/seed_pilot_data.py`
  - Added make target: `seed-pilot`
- Added one-command pilot eval report:
  - New script: `scripts/run_pilot_eval.py`
  - Runs fixed scenario set and reports readiness counts + evidence-backed ratio
  - Added make target: `eval-pilot`
  - Output artifact: `.tmp/pilot-eval/report.json`
- Updated Slack tests to align with structured-intake behavior:
  - Updated `tests/slack/test_command_route.py`
  - Added coverage for missing-field feedback path (`needs_input`)
- Updated docs/planning:
  - `README.md` updated with pilot fast-path commands + structured intake template
  - `docs/ACTION_ITEMS.md` marks Batch M complete and queues final hardening batch

Validation:
- `make lint` passed (`syntax_ok files=70`).
- `make test` passed (`Ran 44 tests ... OK`).
- `make seed-pilot` executed successfully.
- `make eval-pilot` executed successfully and wrote report artifact.

### 2026-05-18 - Batch N Finalized + Launch Packaging Pass
- Completed remaining Batch N implementation:
  - Enhanced Slack intake feedback for malformed team lists with canonical team guidance and alias mapping hints.
  - Deterministic runner now includes stubs for design/support/gtm/security_privacy/tpm lenses via selected-team routing.
  - Added pilot eval threshold gate in `scripts/run_pilot_eval.py` using `--min-evidence-ratio` (non-zero exit on failure).
  - Updated `Makefile` so `make eval-pilot` supports optional `EVAL_MIN_EVIDENCE_RATIO=<value>`.
- Updated tests:
  - `tests/orchestration/test_runner_timeouts.py` now expects partial deterministic output for non-timed-out teams.
  - `tests/slack/test_command_route.py` now validates malformed-team guidance response.
- Tightened packaging docs for launch narrative:
  - Rewrote `README.md` with PM-facing value framing, workflow, and pilot-gate command usage.
  - Updated `docs/ACTION_ITEMS.md` to mark Batch N complete and queue lean Batch O.

### 2026-05-18 - README PRD Style Upgrade (User Request)
- Rewrote `README.md` with sharper PRD-style framing:
  - product summary, problem, users, workflow, MVP scope, outcomes
  - explicit integrations section for live Jira + Confluence connectors
  - explicit note that team lenses use scoped policy and source preferences
  - included canonical team names and alias mapping in Slack brief format
- Preserved quick-start and security defaults while improving positioning language for PM/TPM value narrative.

### 2026-05-18 - README Story Upgrade from ProjectIdeas PDF
- Parsed `/Users/dhruvtoprani/Downloads/ProjectIdeas_Toprani.pdf` and used it to rewrite README with stronger PM/TPM product narrative.
- README now includes:
  - PRD snapshot (users, job, output)
  - clear problem -> thesis -> workflow story
  - team-lens section explicitly covering Jira + Confluence integration by stakeholder lens
  - end-to-end technical architecture and full stack layering
  - Mermaid sequence and architecture diagrams where helpful
  - pilot success criteria and positioning language for portfolio/interview usage.

### 2026-05-18 - README Concision + Emphasis Pass
- Tightened README language to be more direct and concise.
- Added stronger bold emphasis on high-signal product terms (problem, outcome, readiness, stack layers).
- Preserved PRD structure, Jira/Confluence integration narrative, and diagrams while reducing verbosity.
