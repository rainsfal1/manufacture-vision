# Manufacture Vision

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-Streams-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/ONNX-Runtime-005CED?style=flat-square&logo=onnx&logoColor=white" alt="ONNX">
  <img src="https://img.shields.io/badge/MinIO-S3--Compatible-C72E49?style=flat-square&logo=minio&logoColor=white" alt="MinIO">
  <img src="https://img.shields.io/badge/Grafana-Observability-F46800?style=flat-square&logo=grafana&logoColor=white" alt="Grafana">
</p>

<p align="center">
  AI-powered industrial vision platform for PPE compliance, zone intrusion detection, and fire &amp; smoke alerting — edge inference to central dashboard, fully containerised.
</p>

---

## What the platform covers

### Workplace safety and PPE compliance

Automated checks for **helmets, safety vests, and gloves** on detected people, with configurable confidence thresholds and cooldowns so alerts stay actionable. Events include track IDs, zones, and timestamps, backed by short **evidence video clips** stored in object storage — suitable for audits and supervisor review.

**On the roadmap (not in the MVP yet):** richer workplace safety analytics — e.g. systematic unsafe-behavior cues beyond missing PPE, broader hazard heuristics, and deeper tie-ins to site safety programs. The architecture (event spine, retention, UI) is built so those layers can plug in without redoing the pipeline.

### Intrusion and perimeter awareness

**Polygon zones** with enter/exit state machines give you restricted-area and perimeter-style coverage: people entering or leaving defined regions generate **zone enter / zone exit** events and drive the same notification and reporting path as PPE violations. Zones can be managed through the app's zone tooling and synced to edge nodes.

### Fire and smoke detection

The perception stack includes an ONNX-based **fire / smoke** detector running parallel to person/PPE inference. When the model artifact is present, early fire, smoke, or related visual cues raise events, trigger evidence capture, and support faster emergency-response workflows.

> **Note:** place the exported `fire_smoke.onnx` model at `perception-node/models/fire_smoke.onnx`. The environment flag `ENABLE_FIRE_SMOKE` controls whether detections produce events; inference still runs each frame when the model is loaded.

---

## Capability snapshot

| Area | Status | Next |
|------|--------|------|
| Person detection + multi-object tracking | ✅ YOLOv8n + ByteTrack | — |
| PPE (helmet, vest, gloves) | ✅ | Expanded classes / site-specific policies |
| Restricted zones (polygon enter/exit) | ✅ | Schedules, richer perimeter logic |
| Evidence clips (pre/post event) | ✅ MinIO | Retention tiers, legal hold |
| Fire / smoke (visual) | ✅ ONNX model | Tuning, multi-camera correlation |
| Unsafe behaviors & broad hazard taxonomy | Partial (PPE + zones) | Explicit models and rules |
| Central API, dashboard, reports | ✅ | SSO, RBAC hardening |

---

## Stack

| Service | Tech | Port |
|---------|------|------|
| Frontend dashboard | Next.js 14 + TypeScript | 3000 |
| Central backend | FastAPI + PostgreSQL + SQLAlchemy | 8000 |
| Perception node | Python + ONNX Runtime | metrics: 9091 |
| Redis | Redis Streams (event bus) | 6379 |
| PostgreSQL | Event and app persistence | 5432 |
| MinIO | S3-compatible evidence storage | 9000 (console: 9001) |
| Prometheus | Metrics scrape | 9090 |
| Grafana | Dashboards | 3001 |

---

## Quick start

### Prerequisites

- **Docker** and **Docker Compose**
- A demo video at `data/mock_videos/ppe/clip1.mp4` used as the default `INPUT_STREAM` (or point `INPUT_STREAM` at an RTSP URL in `.env`)

### 1. Environment

```bash
cp .env.example .env
```

Local development defaults work out of the box. **Change all secrets before any real deployment.**

### 2. Run everything

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

The central backend applies database migrations on startup. After services are healthy:

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Dashboard |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000/health | Health check |
| http://localhost:8000/metrics | Backend Prometheus metrics |
| http://localhost:9091/metrics | Perception node metrics |
| http://localhost:9090 | Prometheus UI |
| http://localhost:3001 | Grafana |
| http://localhost:9001 | MinIO console |

Demo credentials are defined in `.env.example` — **replace in production**.

---

## Architecture

```
Video input (file or RTSP)
         │
         ▼
 Perception node ──────────────► Redis Stream (vision.events)
         │                                │
         ├── Person + PPE (helmet, vest, gloves)
         ├── Polygon zones (enter / exit)
         ├── Fire / smoke (ONNX)
         ├── ByteTrack multi-object tracking
         └── Evidence clips ──────────► MinIO
                                              │
                                              ▼
                                   Central backend
                                   ├── Persist events (PostgreSQL)
                                   ├── Notification dispatch
                                   └── REST / SSE API
                                              │
                                              ▼
                                   Next.js dashboard
                                   (alerts, analytics, zones, reports)

 Prometheus ◄── /metrics (backend + edge nodes)
      │
      ▼
 Grafana
```

---

## Deployment

### Topology

- **Edge:** perception nodes read camera streams or files, run ONNX inference, upload clips to MinIO, and publish events to Redis Streams.
- **Central:** the backend consumes the stream, persists to PostgreSQL, dispatches notifications, and serves the Next.js dashboard via REST + SSE.

| Compose file | Use |
|-------------|-----|
| `docker/docker-compose.dev.yml` | Single-machine full stack |
| `docker/docker-compose.central.yml` | Redis, Postgres, backend ("datacenter" slice) |
| `docker/docker-compose.edge.yml` | Redis, MinIO, perception node ("plant floor" slice) |

For production splits, point each perception node's `REDIS_URL` and `MINIO_*` at the central services, and set `BACKEND_URL` if nodes should pull zone configuration from the API at startup.

### Video inputs

- **File:** `INPUT_STREAM=/data/mock_videos/ppe/clip1.mp4`
- **RTSP / IP camera:** `INPUT_STREAM=rtsp://user:pass@camera-ip:554/stream`

Each physical source should have a stable `SOURCE_ID` (e.g. `line-3-north`) for multi-camera operations.

### Perception node toggles

| Variable | Effect |
|----------|--------|
| `ENABLE_PPE_COMPLIANCE` | PPE checks on person crops |
| `ENABLE_ZONE_INTRUSION` | Polygon zone state machine |
| `ENABLE_FIRE_SMOKE` | Fire/smoke branch (requires `models/fire_smoke.onnx`) |
| `FIRE_SMOKE_MODEL_PATH` | Override model location |

### Production hardening checklist

1. **Secrets** — rotate `JWT_SECRET`, DB passwords, MinIO keys, and dashboard admin passwords; never commit `.env`
2. **Transport** — terminate TLS at a reverse proxy or cloud LB; use `MINIO_SECURE=true` where applicable
3. **Logs** — set `LOG_FORMAT=json` on backend and nodes to feed your log stack
4. **Postgres** — managed DB or backups + PITR; size for event volume and retention policy
5. **Object storage** — production MinIO cluster or S3-compatible service; tune bucket lifecycle for evidence retention
6. **Redis** — persistence and HA appropriate to your durability needs for the event stream
7. **Observability** — keep Prometheus scrape configs pointed at every node and the API; alert on FPS drops, ingest lag, and error rates

### Scaling

- **Horizontal** — run multiple perception nodes (one per camera or NVR output), each with its own `SOURCE_ID`, writing to the same Redis stream and MinIO bucket
- **Vertical** — ONNX supports CUDA execution providers where available; tune `FPS_LIMIT` and `FRAME_SKIP` to meet SLA
- **Kubernetes** — containers and env vars map cleanly to Deployments (backend), StatefulSets (Postgres/Redis if self-hosted), and DaemonSets or per-camera Jobs for edge inference

---

## Local development (without Docker)

### Infrastructure only

```bash
docker compose -f docker/docker-compose.central.yml up -d
```

### Backend

```bash
cd central-backend
uv sync
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Perception node

```bash
cd perception-node
uv sync
python src/main.py
```

### Frontend

```bash
cd frontend-dashboard
npm install
npm run dev
```

---

## Environment variables

Key variables (full list in `.env.example`):

```env
# Perception
INPUT_STREAM=/path/or/rtsp://...
SOURCE_ID=camera-01
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
ENABLE_FIRE_SMOKE=true

# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/mvision
JWT_SECRET=change-me-in-production
LOG_FORMAT=text   # json in production
```

---

## Database migrations

```bash
cd central-backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
```

---

## Testing

```bash
bash tools/run_acceptance.sh
```

End-to-end checks: Redis stream activity, PostgreSQL persistence, MinIO clips, API health, and `/metrics` on both backend and perception node.

---

## Project structure

```
manufacture-vision/
├── .env.example
├── docker/
│   ├── docker-compose.dev.yml       # Full stack
│   ├── docker-compose.central.yml
│   ├── docker-compose.edge.yml
│   ├── prometheus/
│   └── grafana/
├── central-backend/                 # FastAPI service
├── perception-node/                 # ONNX edge inference
├── frontend-dashboard/              # Next.js dashboard
├── data/
│   └── mock_videos/
├── shared-contracts/                # JSON schemas
└── tools/
    └── run_acceptance.sh
```

---

## Troubleshooting

**Port conflicts**
```bash
docker compose -f docker/docker-compose.dev.yml down
docker compose -f docker/docker-compose.dev.yml up --build
```

**No events from perception node**
- Confirm `INPUT_STREAM` path exists in the container or RTSP is reachable
- Check logs: `docker compose -f docker/docker-compose.dev.yml logs -f perception-node`
- If startup fails loading ONNX, confirm model files are present at the expected paths

**Fresh volumes**
```bash
docker compose -f docker/docker-compose.dev.yml down -v
```
