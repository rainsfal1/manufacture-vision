# Manufacturing Vision Platform — Final Architecture (Grouped Tables)

## 1) Edge Perception Node (On-site, Real-Time)

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| Video Ingestion | **GStreamer** (RTSP) | Stable long-running ingest, decode, reconnect | Prefer **dual-stream** setup: low-res substream for AI, high-res mainstream for evidence |
| Camera/VMS Adapter (Optional but common in factories) | **ONVIF** + VMS/NVR connectors | Discover cameras, manage credentials, standardize RTSP profiles | Manufacturing deployments often inherit VMS/NVR ecosystems |
| Stream Scheduler | **Adaptive FPS + per-stream priority** | Keeps latency bounded under load | Critical/priority zones get higher FPS; non-critical streams throttle |
| Inference Runtime | **ONNX Runtime** | Runs detection models portably | Portable across Linux IPCs/edge servers; avoids vendor lock-in |
| Object Detection | **ONNX-exported detector** (people + PPE + smoke/fire) | Detect workers/PPE/hazards | Keep model “swappable” per module; avoid hard-committing to a single YOLO version |
| Multi-Object Tracking | **ByteTrack** | Persistent IDs, trajectories | Enables zone logic, loitering, intrusion rules, PPE-by-person continuity |
| Spatial Logic | **OpenCV** | Zones, tripwires, homography (optional) | Supports restricted-zone, perimeter lines, machine safety perimeters |
| Event Engine | **State machines + debouncing + cooldowns** | Converts tracks into discrete events | Product value lives here: policy correctness and low false alarms |
| Clip Buffer | **Ring buffer (disk/mem)** | Evidence capture around events | Pre/post-event clip export; configurable retention |
| Telemetry (Edge) | **Metrics + health heartbeat** | Ops visibility | Track FPS, queue depth, drops, reconnects, inference latency |

---

## 2) Internal Event Spine (Edge → Central)

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| Event Transport (MVP) | **Redis Streams** | Reliable event flow with minimal moving parts | Good for first pilots; easy ops |
| Event Transport (Scale) | **NATS** | High-throughput pub/sub for multi-site | Cleaner scaling and fanout than Redis Streams |
| Event Contract | **Versioned JSON schema + typed models** | Ensures consistent payloads across services | Prevents schema drift between edge/backend/dashboard |

**Guidance:** Use **one** internal event spine (Redis Streams *or* NATS). Do not run multiple “core buses” simultaneously.

---

## 3) Central Platform (On-Prem Preferred for Industrial IP/OT Security)

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| API | **FastAPI** | Event ingestion, config, auth, integrations | Keeps central thin; edge does real-time eventing |
| Database | **PostgreSQL** | Events, configs, audit logs | Transactional + audit-friendly |
| Cache | **Redis** | Live feed caching, session state | Improves dashboard responsiveness |
| RBAC/Auth | **JWT + RBAC** | Access control by role/site | Aligns with IT/OT segmentation and least privilege |
| Analytics Jobs | **Python services** | Aggregations, compliance rates, trend reports | Shift-based metrics and site rollups |

---

## 4) Media Storage & Retrieval (Evidence Strategy)

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| Primary Media Store (On-Prem) | **MinIO (S3-compatible)** | Stores event clips and evidence | Default for factories protecting IP/trade secrets |
| Optional Cloud Store | **Cloudflare R2** (S3-compatible) | Low-egress cloud storage | Use only if policy allows off-site media |
| Access Control | **Signed URLs** | Secure clip access | Time-bound access; prevents leakage |
| VMS/NVR Clip Retrieval (Optional) | **Time-range clip fetch via NVR/VMS** | Avoid duplicating full-time recording | Common in manufacturing: store only events + reference NVR for full footage |

**Default posture:** store **event clips only**, not continuous video.

---

## 5) Integration Outputs (Industrial / OT-Friendly Adapters)

| Integration Type | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| IIoT Messaging (Optional output) | **MQTT** | Publish events to plant systems | Treat as **integration adapter**, not internal core bus |
| OT/SCADA Interfaces (Later, if needed) | **OPC UA / Modbus adapters** | Bridge to PLC/SCADA | Common in industrial environments; add when required by buyer |
| Notifications | **Webhooks + Email/SMS/Teams** | Alert routing | Often sufficient for early deployments |
| Ticketing/Incident Mgmt | **Webhook to Jira/ServiceNow** | Incident workflows | Enterprise integration path |

---

## 6) Dashboard & UI

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| Frontend | **Next.js (React)** | Events, playback, analytics, configuration | Role-based views (Safety, Security, Ops) |
| Realtime Feed | **SSE** | Live event streaming | Firewall-friendly; simplest reliable approach |
| Playback | **MP4/HLS** | Evidence review | Supports incident audits and investigations |
| Visualization | **Recharts (or equivalent)** | Compliance & incident analytics | Shift/zone heatmaps, trend lines, SLA metrics |
| Configuration UI | **Zone/policy editor** | Define zones, PPE requirements, schedules | Manufacturing value depends heavily on policy configuration |

---

## 7) Deployment & Operations

| Component | Recommended Technology | Purpose | Notes |
|---|---|---|---|
| Packaging | **Docker** | Reproducible deployment | Per-service Dockerfiles |
| Orchestration (Optional later) | **K3s/Kubernetes** | Multi-node resilience | Not required for MVP; adopt when fleet grows |
| Observability | **Prometheus + Grafana** | Metrics dashboards | Monitor stream health, latency, drops, GPU/CPU, disk |
| Logging | **Structured JSON logs** | Debug + audit trail | Centralize logs for incident investigations |
| Resilience | **Auto-restart + watchdogs** | Reduce downtime | Edge node must self-heal |

---

## Architectural Principles (Manufacturing-Specific)

- **Edge-first inference** to reduce bandwidth and protect plant IP/OT isolation.
- **Bounded latency** via adaptive FPS, bounded queues, and drop policies under load.
- **Event-driven outputs** (alerts + clips + audit logs) instead of storing continuous video by default.
- **Policy/zone configuration is core product value** (PPE-by-zone, schedules, escalation).
- **S3-compatible storage interface** to support on-prem (MinIO) and optional cloud (R2) without lock-in.
- **Integration adapters** (MQTT/OPC UA/Modbus/webhooks) are outputs, not the internal event spine.