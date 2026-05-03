# Phase 10: Deployment & Hardening

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 15: System continues running even if central server is temporarily unreachable
- User story 20: Health and telemetry metrics visible without SSH
- User story 21: Edge node self-recovers from camera disconnects and Redis outages
- User story 22: System packaged in Docker Compose for repeatable deployment

## Blocked by

Phases 1–9

## What to build

Package the full platform as a production-ready Docker Compose deployment and validate the complete system end-to-end. Three Compose files: `docker-compose.edge.yml` (perception node + Redis + MinIO), `docker-compose.central.yml` (FastAPI + PostgreSQL + Redis consumer side), `docker-compose.dev.yml` (full stack locally). All services have auto-restart policies. Structured JSON logging is consistent across all services. The full acceptance test suite runs against VIRAT clips and verifies the end-to-end path from video frame to dashboard alert with evidence clip. Observability: structured logs ship to a centralized log sink; Prometheus + Grafana are scaffolded but optional.

## Architectural decisions

- Docker restart policy: `unless-stopped` for all production services.
- Environment variables for all secrets (database URL, Redis URL, MinIO credentials, JWT secret). No secrets in images.
- Healthchecks defined for every service — Docker Compose `depends_on: condition: service_healthy`.
- Structured JSON logs: every service emits `{ timestamp, level, service, message, ...context }`.
- Acceptance test suite: uses `tools/run_acceptance.sh` as entry point. Runs VIRAT clips, asserts events appear in Redis and PostgreSQL within latency thresholds, and verifies clip appears in MinIO.
- Grafana dashboards: edge node FPS, latency, queue depth, drop rate, Redis consumer lag.

## Acceptance criteria

- [ ] `docker compose -f docker-compose.dev.yml up` brings up full stack with no manual steps.
- [ ] All services have Docker healthchecks; unhealthy services trigger restarts.
- [ ] No secrets hardcoded in Dockerfiles or compose files — all via environment variables.
- [ ] Structured JSON logs emitted by all services, readable without parsing.
- [ ] Acceptance test suite passes: VIRAT clips → events in Redis → persisted in PostgreSQL → clips in MinIO → dashboard shows alert with playable clip.
- [ ] Edge node continues operating if central backend is unreachable (Redis events drop-and-log, inference continues).
- [ ] Prometheus metrics endpoint exposed on edge node and central backend.
- [ ] Grafana dashboard loads and shows live edge node metrics.

## Notes

This is the MVP completion milestone. After this phase, the system is pilotable: plug in a camera (Phase 7), configure zones (Phase 6), and a safety officer gets live alerts with video proof. Phases 11–14 add detection features on top of a stable, deployed platform.
