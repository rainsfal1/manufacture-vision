# Database Migrations

All schema migrations for the `manufacture-vision` central backend, managed with **Alembic**.

Run all pending migrations:
```bash
cd central-backend
uv run alembic upgrade head
```

Roll back one step:
```bash
uv run alembic downgrade -1
```

Check current revision:
```bash
uv run alembic current
```

---

## Migration History

### 001 — Initial Schema
**File:** `001_initial_schema.py`  
**Revises:** _(none — baseline)_  
**Phase:** 4 (Central Backend)

Creates the four core tables that every other phase builds on:

| Table | Purpose |
|-------|---------|
| `events` | One row per raw event consumed from the Redis Stream (`vision.events`). Holds all ZONE_ENTER, ZONE_EXIT, and PPE_VIOLATION events with full payload fields. |
| `zones` | Zone configuration — polygon coordinates, required PPE list, and camera association. Managed via the Phase 6 Zone CRUD API. |
| `policies` | PPE enforcement policies linked to zones. Each policy has an `active` flag; only one policy can be active per zone at a time. |
| `audit_log` | Append-only record of every mutation to zones and policies (create / update / delete / activate / deactivate). Stores actor, action, entity reference, and a JSON diff. |

**Indexes created on `events`:**
- `ix_events_event_ts_ms` — fast time-range queries (used by all event listing and reporting endpoints)
- `ix_events_zone_id` — fast filter by zone
- `ix_events_event_type` — fast filter by event type

---

### 002 — Reporting Indexes
**File:** `002_reporting_indexes.py`  
**Revises:** 001  
**Phase:** 8 (Reporting & Analytics)

Adds two composite indexes to `events` to make the Phase 8 aggregation queries efficient. Without these, the `GROUP BY` queries in `/reports/summary`, `/reports/trend`, and `/reports/export` would require sequential scans as the events table grows.

| Index | Columns | Used by |
|-------|---------|---------|
| `ix_events_type_ts` | `(event_type, event_ts_ms)` | `GET /reports/trend` and `GET /reports/export` — both filter by a specific event_type within a time range |
| `ix_events_zone_ts` | `(zone_id, event_ts_ms)` | `GET /reports/summary` and `GET /reports/trend` with `?zone_id=` filter |

These are additive — no columns are altered, no data migrated.

---

### 003 — Notification Schema
**File:** `003_notification_schema.py`  
**Revises:** 002  
**Phase:** 9 (Outbound Alert Notifications)

Creates two tables for the notification dispatch system.

| Table | Purpose |
|-------|---------|
| `notification_channels` | Where to send alerts — Slack webhooks, arbitrary HTTP endpoints, or email stubs. Config stored as a JSON blob (e.g. `{"url": "..."}` for Slack/webhook, `{"to": "..."}` for email). |
| `notification_rules` | When to fire a channel — maps an `event_type` + optional `zone_id` filter to a channel. `event_type="*"` matches all types; `zone_id=NULL` matches any zone. |

**Indexes created on `notification_rules`:**
- `ix_notification_rules_channel_id` — fast lookup of all rules for a given channel
- `ix_notification_rules_active` — dispatcher loads only active rules on startup and every 60s refresh
