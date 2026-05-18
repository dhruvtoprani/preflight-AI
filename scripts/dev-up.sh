#!/usr/bin/env bash
set -euo pipefail

echo "Starting local infra (Postgres + Redis)..."
docker compose -f infra/docker-compose.yml up -d

echo "Done."
