# Phase 8: Analytics & Compliance

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 11: Compliance rate metrics per zone and per shift
- User story 12: Daily summary of safety incidents
- User story 14: Trend data on intrusion events, PPE violations, and other incidents over time
- User story 24: Export incident logs for a specified time range

## Blocked by

Phase 4, Phase 5

## What to build

Analytics views in the dashboard backed by aggregation API endpoints. Plant managers see compliance rate per zone (percentage of time a zone was violation-free) and per shift (configurable shift windows), incident trend charts over time, and a daily incident summary. Auditors can export incident logs as CSV for a specified date range. All data is derived from the existing `events` table — no new event pipeline changes. Charts use Recharts (or equivalent).

## Architectural decisions

- Aggregation queries run on PostgreSQL directly — no separate analytics service for MVP.
- Shift windows configurable: default 3 shifts × 8 hours. Stored in a `shifts` config table.
- Compliance rate definition: for a given zone in a time window, `1 - (violation_minutes / total_monitored_minutes)`.
- Trend charts: event count per day/week by event type and zone, last 30 days default.
- Export format: CSV. Fields match `events` table columns + human-readable zone label.
- Analytics API routes: `GET /api/v1/analytics/compliance`, `GET /api/v1/analytics/trends`, `GET /api/v1/events/export`.
- Export is synchronous for MVP (streamed CSV response). Background job for large ranges is post-MVP.

## Acceptance criteria

- [ ] Compliance rate chart renders per zone for current shift and last 7 days.
- [ ] Incident trend chart shows event count by type per day for last 30 days.
- [ ] Daily summary view shows total events by type for the current calendar day.
- [ ] `GET /api/v1/events/export?from=<ts>&to=<ts>` returns a valid CSV download.
- [ ] Shift windows configurable without code change.
- [ ] RBAC: `auditor` role can access all analytics and export endpoints.

## Notes

This phase adds reporting on top of existing data — no new events are introduced. The compliance rate calculation depends on knowing when a zone was actively monitored vs. offline, which requires the health heartbeat (established in Phase 4) to be factored into the denominator.
