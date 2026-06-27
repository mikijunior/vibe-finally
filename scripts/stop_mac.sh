#!/usr/bin/env bash
#
# FinAlly stop script (macOS / Linux).
#
# Stops and removes the running FinAlly container. The named volume
# 'finally-data' (which holds the SQLite database) is preserved so
# restarting the app keeps all trades and watchlist state.
#
# Idempotent: safe to run when no container exists.
#
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not on PATH." >&2
    exit 1
fi

# Compose handles both "compose project" and a stray "finally" container.
docker compose -f docker-compose.yml -p finally down 2>/dev/null || true
# Defensive cleanup for the case where someone started with plain `docker run`.
docker rm -f finally 2>/dev/null || true

echo "FinAlly stopped. Data volume 'finally-data' preserved."
