# PreFlight Healthcheck Runbook

## Local Service URLs
1. Orchestrator base: `http://localhost:8000`
2. Slack bot base: `http://localhost:8001`
3. Dashboard base: `http://localhost:8002`

## Health Endpoints
1. Orchestrator basic health: `GET /health`
2. Orchestrator full health: `GET /health/full`
3. Slack bot basic health: `GET /health`
4. Slack bot full health: `GET /health/full`
5. Dashboard basic health: `GET /health`
6. Dashboard full health: `GET /health/full`

## What `/health/full` checks

### Orchestrator
1. Runner mode (`auto|llm|deterministic`)
2. OpenAI key presence
3. Team policy file presence
4. Prompt template directory presence
5. Retrieval index file presence
6. Jira connector credential config presence
7. Confluence connector credential config presence
8. Persistence diagnostics:
   - storage mode (`db|file-fallback`)
   - postgres driver availability (`psycopg`)
   - optional DB connectivity check
   - fallback run-dir writable check
   - retention policy settings

### Slack bot
1. Slack token config presence
2. Slack signing secret presence
3. Slack app token presence
4. Orchestrator reachability (`/health`)

### Dashboard
1. Orchestrator reachability (`/health`)

## Quick Start Commands
1. Start orchestrator:
   - `make run-orchestrator`
2. Start slack-bot:
   - `make run-slack`
3. Start dashboard:
   - `make run-dashboard`
4. Sync live connectors (if Jira/Confluence envs are set):
   - `make sync-live`

## Example checks
1. `curl http://127.0.0.1:8000/health/full`
2. `curl http://127.0.0.1:8001/health/full`
3. `curl http://127.0.0.1:8002/health/full`

## Expected behavior
1. `status=ok` means service is running and core checks passed.
2. `status=degraded` means service is running but one or more critical dependencies are missing/unreachable.

## Notes
1. Missing credential checks are expected in local/dev until env vars are configured.
2. Index file check becomes `ok` after ingestion or connector sync populates the index.
3. DB connectivity checks are opt-in via:
   - `PREFLIGHT_PERSISTENCE_HEALTH_DB_CHECK=true`
   - `PREFLIGHT_PERSISTENCE_STARTUP_DB_CHECK=true`
