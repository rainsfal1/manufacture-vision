# Phase 4: Central Backend — Event Ingestion & Storage

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 20: Health and telemetry metrics visible to IT admin
- User story 21: Edge node self-recovers; central backend is always available
- User story 23: Immutable event log with timestamps, zone IDs, clip references
- User story 24: Export incident logs for a specified time range
- User story 25: Event schema is versioned

## Blocked by

Phase 1

## What to build

The central platform's data layer. A FastAPI service with a Redis Streams consumer that reads from `vision.events`, validates event schema version, and persists events to PostgreSQL. JWT-based auth with RBAC is established here — all future API endpoints build on this foundation. A media auth service generates time-bound signed URLs for MinIO clip access. Core query API endpoints expose event filtering by site, zone, event type, and time range. A health endpoint reports consumer lag and service status.

## Architectural decisions

- PostgreSQL tables: `events` (id, event_type, event_ts_ms, source_id, site_id, track_id, zone_id, confidence, bbox, clip_ref, raw_payload, created_at), `zones` (id, source_id, site_id, label, polygon_points, active), `policies` (id, zone_id, feature_type, config_json), `audit_log` (append-only).
- Redis consumer uses consumer groups for exactly-once processing semantics.
- Schema version mismatch: log warning, persist raw_payload, do not drop.
- JWT tokens: short-lived access tokens + refresh tokens. RBAC roles: `safety_officer`, `plant_manager`, `it_admin`, `auditor`.
- Signed URL TTL: configurable, default 1 hour. Generated on demand, never stored.
- All API routes prefixed `/api/v1/`.
- Database migrations managed via Alembic.

## Acceptance criteria

- [ ] Redis consumer reads from `vision.events` and persists all events to PostgreSQL.
- [ ] Schema version mismatch is logged and does not drop events.
- [ ] `GET /api/v1/events` supports filtering by `event_type`, `zone_id`, `source_id`, `from_ts`, `to_ts`.
- [ ] `GET /api/v1/events/{id}/clip-url` returns a signed MinIO URL for the clip.
- [ ] JWT auth enforced on all endpoints; unauthorized requests return 401.
- [ ] RBAC enforced: auditor role can read events but cannot write config.
- [ ] `GET /api/v1/health` reports consumer lag and database connectivity.
- [ ] Alembic migrations run cleanly on fresh PostgreSQL instance.
- [ ] FastAPI and PostgreSQL run in Docker.

## Notes

SSE broadcaster for live dashboard updates is NOT in this phase — that is Phase 5. This phase makes events queryable; Phase 5 makes them stream in real time to the UI. Zone/policy config API endpoints are in Phase 6.
