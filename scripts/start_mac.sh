#!/usr/bin/env bash
#
# FinAlly start script (macOS / Linux).
#
# Builds the Docker image if it does not yet exist, then starts the
# FinAlly container via docker compose. The container serves the full
# app (frontend + backend + SSE + LLM) on http://localhost:8000.
#
# Idempotent: re-running on a healthy container exits 0 with a notice.
#
# Usage:
#   ./scripts/start_mac.sh           # start (build if needed)
#   ./scripts/start_mac.sh --build   # force a rebuild before starting
#
set -euo pipefail

cd "$(dirname "$0")/.."

FORCE_BUILD=0
if [ "${1:-}" = "--build" ]; then
    FORCE_BUILD=1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not on PATH." >&2
    echo "Install Docker Desktop (macOS) or docker-ce (Linux) and try again." >&2
    exit 1
fi

# If a container named "finally" is already running, treat as idempotent.
if docker ps -q -f name=finally | grep -q .; then
    echo "FinAlly is already running at http://localhost:8000"
    exit 0
fi

# Build the image if it does not exist (or if --build was passed).
if [ "$FORCE_BUILD" = "1" ] || ! docker image inspect finally >/dev/null 2>&1; then
    echo "Building FinAlly image (this can take a few minutes on first run)..."
    docker compose -f docker-compose.yml -p finally build
fi

echo "Starting FinAlly container..."
docker compose -f docker-compose.yml -p finally up -d

# Wait up to 30s for the /api/health endpoint to respond.
echo "Waiting for FinAlly to be ready..."
for i in $(seq 1 30); do
    if curl -fsS http://localhost:8000/api/health >/dev/null 2>&1; then
        echo ""
        echo "FinAlly is running at http://localhost:8000"
        exit 0
    fi
    sleep 1
done

echo ""
echo "WARNING: FinAlly did not respond to /api/health within 30s." >&2
echo "The container may still be starting. Check 'docker logs finally'." >&2
exit 1
