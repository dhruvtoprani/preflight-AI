#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/.tmp/local-stack-logs"
mkdir -p "${LOG_DIR}"

PYTHONPATH_VALUE="${ROOT_DIR}/packages/schemas/src:${ROOT_DIR}/packages/shared-utils/src:${ROOT_DIR}/services/orchestrator/src:${ROOT_DIR}/services/ingestion/src:${ROOT_DIR}/services/retrieval/src:${ROOT_DIR}/apps/slack-bot/src:${ROOT_DIR}/apps/dashboard/src"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT INT TERM

start_service() {
  local name="$1"
  local port="$2"
  local module="$3"
  local logfile="${LOG_DIR}/${name}.log"

  echo "Starting ${name} on :${port} (log: ${logfile})"
  PYTHONPATH="${PYTHONPATH_VALUE}" uvicorn "${module}" --port "${port}" >"${logfile}" 2>&1 &
  PIDS+=("$!")
}

start_service "orchestrator" "8000" "orchestrator.main:app"
start_service "slack-bot" "8001" "slack_bot.main:app"
start_service "dashboard" "8002" "dashboard_app.main:app"

echo "Local stack is up. Press Ctrl+C to stop all services."
echo "- Orchestrator: http://127.0.0.1:8000"
echo "- Slack bot: http://127.0.0.1:8001"
echo "- Dashboard: http://127.0.0.1:8002"

echo "Streaming service pids: ${PIDS[*]}"
wait
