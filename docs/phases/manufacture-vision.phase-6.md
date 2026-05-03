# Phase 6: Zone & Policy Configuration

> Feature: Manufacture Vision Platform
> Linear project: manufacture-vision
> PRD: /docs/manufacture-vision-platform.prd.md
> Status: Planned

## User stories covered

- User story 8: Define which zones require which PPE by zone
- User story 13: Configure zone polygons through the UI without engineering support
- User story 19: Configure edge node via config file (zones, camera sources, model settings)

## Blocked by

Phase 4, Phase 5

## What to build

A zone and policy editor in the dashboard and the backend APIs that support it. Safety officers and plant managers can open a camera view, draw polygon zones directly on a snapshot, label them, and assign PPE requirements per zone. Configurations are saved to PostgreSQL via the config API. The edge node polls the central backend for zone and policy updates at a configurable interval, replacing the static `zones.json` file as the source of truth. The config API also exposes endpoints for reading and updating zone definitions programmatically.

## Architectural decisions

- Zone editor UI: polygon drawn by clicking points on a camera snapshot image. Polygon stored as ordered list of `[x, y]` pixel coordinates normalized to `[0,1]` range for resolution independence.
- Config API routes: `GET/POST/PUT /api/v1/zones`, `GET/PUT /api/v1/policies/{zone_id}`.
- Edge polling interval: configurable, default 60 seconds. Edge applies new config without restart.
- Backward compatibility: `zones.json` file on edge still works as a fallback if central is unreachable.
- PPE policy stored in `policies` table: `{ zone_id, feature_type: "ppe", config: { required_ppe: ["helmet", "vest"] } }`.
- Zone changes take effect on next edge poll cycle — no real-time push to edge in MVP.

## Acceptance criteria

- [ ] Plant manager can draw a polygon zone on a camera snapshot in the dashboard UI.
- [ ] Zone label and required PPE items are configurable per zone through the UI.
- [ ] Zone config saved via `POST /api/v1/zones` and persisted to PostgreSQL.
- [ ] Edge node polls `GET /api/v1/zones?source_id=<id>` and applies updated zone config within 2 poll cycles.
- [ ] Updated zone config takes effect without restarting the edge node.
- [ ] `zones.json` fallback still works when central backend is unreachable.
- [ ] RBAC: only `safety_officer`, `plant_manager`, `it_admin` can write zone/policy config.

## Notes

This phase makes the system configurable by non-engineers for the first time. Before this, zone changes required editing `zones.json` on the edge node directly. After this, zones are managed through the UI.
