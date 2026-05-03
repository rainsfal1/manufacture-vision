#!/usr/bin/env bash
# demo_sequential.sh — Start perception nodes one at a time for demos.
#
# Usage:
#   bash tools/demo_sequential.sh           # all 4 cameras, 30s apart
#   bash tools/demo_sequential.sh 60        # all 4 cameras, 60s apart
#   bash tools/demo_sequential.sh 0 zone    # single camera by name (no wait)
#
# Camera names: zone | helmet | no-helmet | fire
# Run from the repo root (manufacturing-vision-mvp/).

set -euo pipefail

COMPOSE="docker compose -f docker/docker-compose.dev.yml"
DELAY="${1:-30}"
SINGLE="${2:-}"

start_node() {
  local name="$1"
  local service="perception-node-${name}"
  echo ""
  echo ">>> Starting ${service} (camera: ${name})"
  $COMPOSE up -d "$service"
}

# Always start infrastructure first
echo "=== Starting infrastructure (redis, postgres, minio, central-backend, frontend) ==="
$COMPOSE up -d redis postgres minio
echo "--- Waiting 15s for infrastructure to become healthy ---"
sleep 15

$COMPOSE up -d central-backend
echo "--- Waiting 20s for backend to become healthy ---"
sleep 20

$COMPOSE up -d frontend-dashboard prometheus grafana
echo ""
echo "Dashboard: http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
echo ""

if [[ -n "$SINGLE" ]]; then
  start_node "$SINGLE"
  echo ""
  echo "=== Single-camera mode: ${SINGLE} is running ==="
  echo "Press Ctrl-C to stop, or run 'docker compose -f docker/docker-compose.dev.yml down' to tear down."
  exit 0
fi

# Sequential roll-out: one camera every DELAY seconds
CAMERAS=(zone helmet no-helmet fire)
for cam in "${CAMERAS[@]}"; do
  start_node "$cam"
  if [[ "$cam" != "fire" ]]; then
    echo "--- Waiting ${DELAY}s before next camera (Ctrl-C to stop here) ---"
    sleep "$DELAY"
  fi
done

echo ""
echo "=== All cameras running ==="
echo "Logs: docker compose -f docker/docker-compose.dev.yml logs -f perception-node-zone"
