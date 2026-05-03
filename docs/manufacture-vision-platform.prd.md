# PRD: Manufacture Vision Platform

> Status: Draft
> Linear project: manufacture-vision
> Created: 2026-03-19

---

## Problem Statement

Manufacturing facilities run continuous CCTV coverage but have no automated intelligence layer on top of it. Safety officers manually review footage after incidents rather than preventing them in real time. PPE violations go unlogged, restricted zones get breached without immediate alerts, and when an incident does occur, there is no reliable video evidence tied directly to the triggering event. The result is a reactive safety posture, poor audit trails, and high manual monitoring burden — all in an environment where a single incident can mean regulatory fines, shutdowns, or injury.

---

## Solution

An edge-first, real-time situational awareness platform that ingests CCTV/RTSP streams, runs AI inference on the edge, and converts raw video into structured safety events with attached video evidence. The platform produces alerts, evidence clips, and compliance analytics — without replacing existing camera infrastructure. It functions as an intelligence layer: the safety officer still has their cameras and NVR, but now every zone violation, PPE breach, or intrusion triggers an immediate alert with a 10-second evidence clip they can play back instantly.

The platform is modular. Six detection features are built on a shared perception foundation (detect → track → zone → event). Adding a new feature means adding a detection class and policy rule — not rebuilding the pipeline.

---

## User Stories

### Safety Officer
1. As a safety officer, I want to receive a real-time alert when a worker enters a restricted zone without authorization, so that I can respond before an accident occurs.
2. As a safety officer, I want each alert to include a video clip of the incident, so that I can confirm it was a genuine violation and not a false alarm.
3. As a safety officer, I want to see which zone was breached, which camera caught it, and at what time, so that I can dispatch the right response.
4. As a safety officer, I want to see a live feed of active alerts across all monitored zones in the facility, so that I always know the current safety state.
5. As a safety officer, I want alerts to remain visible until I acknowledge them, so that nothing slips through during busy shifts.
6. As a safety officer, I want to search incident history by date, zone, and event type, so that I can investigate patterns and recurring violations.
7. As a safety officer, I want to play back the evidence clip for any historical incident, so that I can use it in disciplinary proceedings or regulatory audits.
8. As a safety officer, I want to define which zones require which PPE (e.g., hard hats in Zone A, vests in Zone B), so that the system enforces the right policy per area.
9. As a safety officer, I want to be notified immediately when a worker is detected without required PPE in a controlled zone, so that I can intervene before a compliance violation is logged.
10. As a safety officer, I want PPE alerts to include a clip showing the worker and the missing equipment, so that the violation is visually verifiable.

### Plant / Operations Manager
11. As a plant manager, I want to see compliance rate metrics per zone and per shift, so that I can identify which areas or time periods have the most violations.
12. As a plant manager, I want to review a daily summary of safety incidents, so that I can report on facility safety performance without manually reviewing footage.
13. As a plant manager, I want to configure zone polygons through the UI without engineering support, so that I can update monitored areas when the factory floor layout changes.
14. As a plant manager, I want to view trend data on intrusion events, PPE violations, and other incidents over time, so that I can demonstrate safety improvements to stakeholders.
15. As a plant manager, I want the system to continue running even if the cloud or central server is temporarily unreachable, so that edge monitoring never goes dark due to a network issue.

### Facility / IT Admin
16. As an IT admin, I want the system to connect to our existing RTSP cameras via ONVIF discovery, so that I don't have to replace camera infrastructure.
17. As an IT admin, I want all video evidence stored on-premises in MinIO, so that no factory footage leaves the facility network.
18. As an IT admin, I want signed URLs for clip access, so that evidence is accessible to authorized users without exposing the storage backend directly.
19. As an IT admin, I want to configure the edge node via a config file (zones, camera sources, model settings), so that the deployment is repeatable and auditable.
20. As an IT admin, I want health and telemetry metrics (FPS, latency, queue depth) visible in the dashboard, so that I can monitor node performance without SSH access.
21. As an IT admin, I want the edge node to self-recover from camera disconnects and Redis outages without manual intervention, so that the system is always-on.
22. As an IT admin, I want the system packaged in Docker Compose, so that I can deploy and upgrade it without custom provisioning work.

### Compliance / Audit
23. As a compliance auditor, I want an immutable event log with timestamps, zone IDs, and evidence clip references, so that I can produce a verifiable audit trail for regulators.
24. As a compliance auditor, I want to export incident logs for a specified time range, so that I can submit them as part of a regulatory review.
25. As a compliance auditor, I want the event schema to be versioned, so that logs remain interpretable even after the platform is updated.

---

## Implementation Decisions

### Architecture: Edge-First, Event-Driven

All AI inference runs on the edge node. The central platform never receives raw video — only structured JSON events and references to stored clips. This protects factory IP, minimizes bandwidth, and ensures real-time inference is not dependent on network conditions.

The internal event spine uses Redis Streams for the MVP (single-site, low volume). The architecture uses `site_id` and versioned event envelopes throughout, so migrating to NATS for multi-site scale is a configuration change, not a rewrite.

### Module 1: Edge Perception Node

**Stream Adapter**
- MP4 adapter for Step 1 (complete). RTSP adapter for live deployment.
- Interface: `(frame: ndarray, pts_ms: int)` tuples — stable across adapter implementations.
- Dual-stream split: low-res substream to inference queue, high-res mainstream to ring buffer.
- ONVIF discovery + RTSP profile negotiation for VMS/NVR environments.

**Frame Buffer**
- Bounded queue (max 5 frames), drop-oldest policy.
- Drop counter exposed to telemetry.
- Complete (Step 1).

**ONNX Detection Runner**
- Runs YOLOv8n (or equivalent) via ONNX Runtime — no PyTorch at inference time.
- Detection classes are model-dependent and swappable per feature (person, PPE classes, fire/smoke).
- Output: `[bbox, confidence, class_id]` per frame.

**ByteTrack**
- Assigns stable track IDs across frames.
- Track state: `track_id`, `bbox`, `last_seen_pts`, `age`.
- Complete (Step 1).

**Spatial Engine**
- Zones loaded from `zones.json`, keyed by `source_id`.
- Zone types: polygon areas (primary), tripwires (later).
- Footpoint rule: bottom-center of bbox for zone membership — mandatory.
- Homography optional (post-MVP for top-down mapping).

**Event Engine**
- Hysteresis state machine: N consecutive frames required before transition fires (anti-flicker).
- Debouncer: cooldown per track × zone pair to suppress repeated events for the same continuous condition.
- Policy layer: per-zone rules (e.g., PPE required in Zone A, restricted access in Zone B).
- Outputs structured events only on transitions.

**Evidence Pipeline**
- Ring buffer: retains last N seconds of high-res frames in memory/disk.
- Clip exporter: on event trigger, slices `[t-5s, t+5s]` window from ring buffer.
- S3 uploader: async upload to MinIO; attaches `clip_ref` to event payload before spine publish.
- If MinIO is unreachable: event publishes without `clip_ref`; clip upload retried in background.

**Output Publishers**
- Redis Streams publisher (`vision.events`): primary output. Fire-and-forget; outage drops event and logs counter.
- Webhook publisher: optional integration output for external systems.
- MQTT publisher: optional IIoT integration output for plant systems.

**Telemetry & Health**
- Metrics: ingest FPS, processed FPS, queue depth, dropped frames, inference latency, active track count, last event timestamp.
- Health heartbeat published on a separate Redis key/stream.
- Rich console UI for local operator visibility.

### Module 2: Shared Event Contracts

Versioned JSON schemas in `shared-contracts/schemas/`:
- `event_envelope.json`: base fields present on every event (`schema_version`, `event_type`, `event_ts_ms`, `source_id`, `site_id`, `track_id`, `confidence`, `bbox`, `clip_ref?`)
- `ppe_event.json`: extends envelope with `zone_id`, `missing_ppe[]`, `required_ppe[]`
- `intrusion_event.json`: extends envelope with `zone_id`, `zone_label`
- `fire_event.json`: extends envelope with `zone_id`, `detection_class` (fire | smoke)
- `system_health.json`: telemetry heartbeat schema

Schema validation runs at edge before publish and at central on consume. Schema version mismatch logs a warning but does not drop the event.

### Module 3: Central Platform (FastAPI)

**Event Consumer**
- Reads from Redis Streams (`vision.events`).
- Validates event schema version.
- Persists to PostgreSQL events table.
- Fans out to SSE broadcaster for live dashboard updates.

**API Layer**
- Event query endpoints: filter by site, zone, event type, time range.
- Config endpoints: zone definitions, PPE policies per zone.
- Media auth endpoint: generates signed MinIO URLs (time-bound).
- Auth: JWT-based. RBAC roles: safety officer, plant manager, IT admin, auditor.

**PostgreSQL Schema (core tables)**
- `events`: id, event_type, event_ts_ms, source_id, site_id, track_id, zone_id, confidence, bbox, clip_ref, raw_payload, created_at
- `zones`: id, source_id, site_id, label, polygon_points, active
- `policies`: id, zone_id, feature_type, config_json
- `audit_log`: append-only record of all acknowledged/exported events

**SSE Broadcaster**
- Pushes new events to connected dashboard clients in real time.
- Firewall-friendly (HTTP long-poll fallback not required for MVP).

**Media Auth Service**
- Generates time-bound signed URLs for MinIO clip access.
- Clips never served directly; always proxied through signed URL.

**Integration Adapters**
- Webhook router: configurable outbound webhooks on event types.
- MQTT bridge: publishes events to plant MQTT broker.
- Both are output adapters — not internal bus components.

### Module 4: Frontend Dashboard (Next.js)

**Real-Time Alert Feed**
- SSE connection to central backend.
- Alert card per event: timestamp, zone, event type, camera, thumbnail or clip preview.
- Unacknowledged alerts visually distinct.

**Incident History Table**
- Filterable by date range, zone, event type, camera.
- Each row links to evidence clip playback.

**Video Player**
- Plays MinIO clips via signed URLs.
- Overlays: bbox, track ID, zone outline (from event metadata).

**Zone / Policy Configuration UI**
- Draw zone polygons on camera snapshot.
- Assign PPE requirements per zone.
- Save to central backend config API.

**Analytics**
- Compliance rate per zone and per shift.
- Incident trend charts.
- Recharts (or equivalent).

### Detection Features

All 6 features share the same perception pipeline (ingest → detect → track → spatial → event engine). Each feature adds:
- A detection class (or reuses person class with attribute detection for PPE).
- A policy rule in the event engine.
- An event schema extending the base envelope.

| Feature | Detection Approach | Event Type |
|---|---|---|
| PPE Compliance | Person + attribute detection (helmet, vest, gloves) | `PPE_VIOLATION` |
| Workplace Safety / Intrusion | Person + zone policy (restricted area) | `ZONE_ENTER`, `ZONE_EXIT` |
| Equipment & Machine Monitoring | Object detection (machine areas) + idle/activity rules | `MACHINE_IDLE`, `UNAUTHORIZED_USAGE` |
| Assembly Line Optimization | Person tracking + dwell time + throughput metrics | `BOTTLENECK_DETECTED`, `IDLE_STATION` |
| Intrusion & Perimeter Security | Person + tripwire + after-hours schedule rules | `PERIMETER_BREACH`, `AFTER_HOURS_PRESENCE` |
| Fire & Smoke Detection | Dedicated fire/smoke detection model | `FIRE_DETECTED`, `SMOKE_DETECTED` |

MVP delivers: Workplace Safety / Intrusion (Step 1 foundation, complete) and PPE Compliance (Step 2).

### Deployment

- Each service has a Dockerfile.
- `docker-compose.edge.yml`: perception node + Redis + MinIO.
- `docker-compose.central.yml`: FastAPI + PostgreSQL + Redis (consumer side).
- `docker-compose.dev.yml`: full stack locally.
- Observability: Prometheus + Grafana (post-MVP); structured JSON logs from day one.
- Edge node must auto-restart on crash (Docker restart policy).

---

## Testing Decisions

**What makes a good test for this platform:**
Tests should verify external behavior — does the system emit the right event when a person enters a zone, does the API return the right filtered results, does the clip get attached to the event. Tests should not assert on internal implementation details like queue internals or model weights.

**Modules to test:**

- **Spatial Engine**: Unit-testable in pure Python. Given a polygon and a footpoint, does `is_in_zone()` return correct results? Edge cases: boundary-crossing, concave polygons.
- **Event Engine / State Machine**: Unit-testable. Given a sequence of per-frame zone membership booleans, does the hysteresis machine emit events at the correct frame threshold? Does the debouncer suppress repeat events within cooldown?
- **Event Schema Validation**: Unit-testable. Given a crafted payload, does validation pass/fail correctly per schema version?
- **Evidence Pipeline**: Integration-testable. Given a triggered event, does the clip exporter produce a file in the correct time window, and does the uploader attach a `clip_ref` to the event?
- **Central API**: Integration tests against a test PostgreSQL instance. Filter queries, signed URL generation, auth/RBAC enforcement.
- **End-to-end acceptance**: Run 2–3 VIRAT clips in paced mode, assert ≥1 ZONE_ENTER and ZONE_EXIT appear in Redis within latency thresholds (≤500ms steady-state).

**Prior art in codebase:**
`tools/validate_schemas.py` and `tools/run_acceptance.sh` are the existing test scaffolding to build from.

---

## Out of Scope

- **Multi-site management**: architecture is site_id-ready but MVP targets a single edge node.
- **K3s / Kubernetes orchestration**: Docker Compose is sufficient for pilot deployments.
- **OPC UA / Modbus / SCADA integration**: MQTT webhook adapters cover industrial output needs for MVP.
- **Pixel-perfect consumer UI**: dashboard must be functional, not polished.
- **Mobile app**: web dashboard only.
- **Continuous video recording**: event clips only; NVR handles full recording.
- **Cloud storage (Cloudflare R2)**: MinIO on-prem only for MVP.
- **Assembly Line Optimization and Equipment Monitoring**: post-MVP detection features (modules 3 and 4).
- **GPU inference acceleration**: ONNX Runtime on CPU for MVP; GPU runtime is a drop-in swap.
- **User self-registration / SSO**: manual JWT provisioning for pilot accounts.

---

## Further Notes

- The perception node uses PyAV (not OpenCV) for PTS-accurate frame extraction. This is a hard requirement for temporal correctness of evidence clips.
- The dual-stream architecture (low-res for AI, high-res for evidence) is load-bearing for clip quality. The inference substream runs at reduced resolution; the ring buffer captures the full-res mainstream.
- The `clip_ref` field in the event envelope is what transforms an alert into auditable evidence. Every event should carry a clip_ref once the evidence pipeline is in place.
- Event schemas are versioned (`schema_version: "1.0"`). Any breaking schema change requires a version bump and a migration plan for stored events.
- Zone configuration (`zones.json`) is currently file-based on the edge. The central policy API will eventually be the source of truth; the edge polls for updates.
- RTSP reconnection behavior must be implemented with backoff and a watchdog. Camera disconnects in manufacturing environments are common and must not crash the node.
