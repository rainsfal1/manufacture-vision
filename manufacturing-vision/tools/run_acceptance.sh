#!/bin/bash
set -e

PASS=0
FAIL=0

assert() {
    local label="$1"
    local result="$2"
    if [ "$result" = "1" ]; then
        echo "[PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $label"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Manufacture Vision — Full E2E Acceptance Test ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"

# ---------------------------------------------------------------------------
# 1. Start infra services
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 1: Starting infrastructure services ---"
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" up -d redis postgres minio

echo "Waiting for Redis..."
until docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do sleep 1; done
echo "Redis ready."

echo "Waiting for PostgreSQL..."
until docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" exec -T postgres pg_isready -U mvision 2>/dev/null; do sleep 2; done
echo "PostgreSQL ready."

echo "Waiting for MinIO..."
until curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; do sleep 2; done
echo "MinIO ready."

# ---------------------------------------------------------------------------
# 2. Start central-backend (runs migrations via entrypoint.sh)
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 2: Starting central-backend ---"
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" up -d central-backend

echo "Waiting for central-backend health check..."
RETRIES=30
until curl -sf http://localhost:8000/health >/dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    sleep 2
    RETRIES=$((RETRIES - 1))
done
assert "central-backend /health returns 200" "$(curl -sf http://localhost:8000/health >/dev/null 2>&1 && echo 1 || echo 0)"

# ---------------------------------------------------------------------------
# 3. Run perception-node for 30 seconds to generate events
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 3: Running perception-node (30s) ---"
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" up -d perception-node
sleep 30
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" stop perception-node

# ---------------------------------------------------------------------------
# 4. Assertions
# ---------------------------------------------------------------------------
echo ""
echo "--- Step 4: Assertions ---"

# 4a. Events in Redis stream
REDIS_COUNT=$(docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" exec -T redis \
    redis-cli XLEN vision.events 2>/dev/null || echo "0")
assert "Events in Redis stream (vision.events > 0)" "$([ "${REDIS_COUNT:-0}" -gt 0 ] && echo 1 || echo 0)"

# 4b. Events persisted to PostgreSQL
PG_COUNT=$(docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" exec -T postgres \
    psql -U mvision -d mvision -t -c "SELECT COUNT(*) FROM events WHERE event_type IS NOT NULL;" 2>/dev/null | tr -d ' ' || echo "0")
assert "Events persisted to PostgreSQL (events > 0)" "$([ "${PG_COUNT:-0}" -gt 0 ] && echo 1 || echo 0)"

# 4c. MinIO has at least one clip
MINIO_CLIPS=$(docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" exec -T minio \
    sh -c 'ls /data/vision-evidence/clips/ 2>/dev/null | wc -l' | tr -d ' ' || echo "0")
assert "MinIO has at least one evidence clip" "$([ "${MINIO_CLIPS:-0}" -gt 0 ] && echo 1 || echo 0)"

# 4d. Backend /events API returns 200 with data
EVENTS_RESP=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/events 2>/dev/null || echo "000")
assert "Backend /events API returns 2xx" "$([ "${EVENTS_RESP}" -ge 200 ] && [ "${EVENTS_RESP}" -lt 300 ] && echo 1 || echo 0)"

# 4e. /metrics endpoint on central-backend
BACKEND_METRICS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/metrics 2>/dev/null || echo "000")
assert "central-backend /metrics returns 200" "$([ "$BACKEND_METRICS" = "200" ] && echo 1 || echo 0)"

# 4f. /metrics endpoint on perception-node
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" up -d perception-node
sleep 5
EDGE_METRICS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:9091/metrics 2>/dev/null || echo "000")
assert "perception-node /metrics returns 200" "$([ "$EDGE_METRICS" = "200" ] && echo 1 || echo 0)"
docker compose -f "$DOCKER_DIR/docker-compose.dev.yml" stop perception-node

# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
