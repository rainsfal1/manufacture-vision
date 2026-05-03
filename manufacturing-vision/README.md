# Manufacture Vision

**Manufacture Vision** is an AI vision platform for industrial sites: it connects cameras at the edge to a central control plane so teams can enforce **PPE compliance**, watch **restricted and perimeter zones**, and get early signal on **fire and smoke** — with evidence clips, live dashboards, and operations-grade observability.

The MVP ships a full reference stack (perception nodes, API, web UI, storage, metrics) so you can run everything locally or split **edge** and **central** for production-style deployment.

---

## What the platform covers

### Workplace safety and PPE compliance

Automated checks for **helmets, safety vests, and gloves** on detected people, with configurable confidence and cooldowns so alerts stay actionable. Events include track IDs, zones, and timestamps, backed by short **evidence video clips** stored in object storage — suitable for audits and supervisor review.

**On the roadmap (not in the MVP yet):** richer **workplace safety** analytics — e.g. systematic **unsafe-behavior** cues beyond missing PPE, broader **hazard** heuristics, and deeper tie-ins to site safety programs and guidelines. The architecture (event spine, retention, UI) is built so those layers can plug in without redoing the pipeline.

### Intrusion and perimeter awareness

**Polygon zones** with enter/exit state machines give you **restricted-area** and **perimeter-style** coverage: people entering or leaving defined regions generate **zone enter / zone exit** events and can drive the same notification and reporting path as PPE violations. Zones can be managed through the app’s zone tooling and synced to edge nodes where supported.


### Fire and smoke detection

The perception stack includes an ONNX-based **fire / smoke** detector (full-frame, parallel to person/PPE). When the model artifact is present, early **fire**, **smoke**, or related visual cues can raise events, trigger evidence capture, and support faster **emergency response** workflows alongside your existing monitoring.

**Note:** place the exported **`fire_smoke.onnx`** model at `perception-node/models/fire_smoke.onnx` (see [docs/phases/phase-14-implementation-plan.md](docs/phases/phase-14-implementation-plan.md) for export steps). The perception node loads this ONNX session at startup, so **the file must be present** for the node to run. Environment flag **`ENABLE_FIRE_SMOKE`** controls whether detections produce events and evidence; inference still runs each frame when the model is loaded.

---

## Capability snapshot

| Area | In this repo today | Planned / next |
|------|-------------------|----------------|
| Person detection + multi-object tracking | Yes (YOLOv8n + ByteTrack) | — |
| PPE (helmet, vest, gloves) | Yes | Expanded classes / site-specific policies |
| Restricted zones (polygon enter/exit) | Yes | Schedules, richer perimeter logic |
| Evidence clips (pre/post event) | Yes (MinIO) | Retention tiers, legal hold |
| Fire / smoke (visual) | Yes, with ONNX model | Tuning, multi-camera correlation |
| Unsafe behaviors & broad hazard taxonomy | Partially (via PPE + zones) | Explicit models and rules |
| Central API, dashboard, reports | Yes | SSO, RBAC hardening |

---

## Stack

| Service | Tech | Default port |
|--------|------|----------------|
| Frontend dashboard | Next.js 14 + TypeScript | 3000 |
| Central backend | FastAPI + PostgreSQL + SQLAlchemy | 8000 |
| Perception node | Python + ONNX Runtime | — (metrics 9091) |
| Redis | Redis Streams (event bus) | 6379 |
| PostgreSQL | Event and app persistence | 5432 |
| MinIO | S3-compatible evidence storage | 9000 (console 9001) |
| Prometheus | Metrics | 9090 |
| Grafana | Dashboards | 3001 |

---

## Quick start (full stack)

### Prerequisites

- **Docker** and **Docker Compose**
- A demo video at `data/mock_videos/ppe/clip1.mp4` used as the default `INPUT_STREAM` (or point `INPUT_STREAM` at an **RTSP** URL in `.env`)

### 1. Environment

```bash
cp .env.example .env
```

Local development defaults are intended to work out of the box; **change all secrets before any real deployment**.

### 2. Run everything

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

The central backend applies database migrations on startup. After services are healthy, use the URLs below.

### Service URLs (development)

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Dashboard |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000/health | Health check |
| http://localhost:8000/metrics | Prometheus metrics (backend) |
| http://localhost:9091/metrics | Prometheus metrics (perception node) |
| http://localhost:9090 | Prometheus UI |
| http://localhost:3001 | Grafana |
| http://localhost:9001 | MinIO Console |

Demo credentials are defined in `.env` / `.env.example` (e.g. dashboard and Grafana users — **replace in production**).

---

## Deployment

### Topology

- **Edge:** one or more **perception nodes** read camera streams or files, run ONNX inference, upload clips to **MinIO** (or compatible S3), and publish structured events to **Redis Streams**.
- **Central:** the **backend** consumes the stream, persists to **PostgreSQL**, dispatches notifications, and exposes **REST + Web/SSE** APIs for the **Next.js** dashboard.

You can run both sides on one machine (development compose) or **split**:

| Compose file | Typical use |
|-------------|-------------|
| [docker/docker-compose.dev.yml](docker/docker-compose.dev.yml) | Single-machine full stack |
| [docker/docker-compose.central.yml](docker/docker-compose.central.yml) | Redis, Postgres, backend — “datacenter” slice |
| [docker/docker-compose.edge.yml](docker/docker-compose.edge.yml) | Redis, MinIO, perception node — “plant floor” slice |

For production splits, point each perception node’s `REDIS_URL` and `MINIO_*` settings at the central or shared services reachable over your network; set `BACKEND_URL` if nodes should pull zone configuration from the API at startup.

### Video inputs

- **File path:** `INPUT_STREAM=/data/mock_videos/ppe/clip1.mp4` (container path — mount host video under `data/` as in compose).
- **RTSP / IP camera:** `INPUT_STREAM=rtsp://user:pass@camera-ip:554/stream` — ensure latency and FPS limits (`FPS_LIMIT`) match camera capability.

Each physical source should have a stable **`SOURCE_ID`** (e.g. `line-3-north`) for multi-camera operations.

### Perception node toggles

Key environment variables (see `perception-node/src/config/settings.py`):

- `ENABLE_PPE_COMPLIANCE` — PPE checks on person crops  
- `ENABLE_ZONE_INTRUSION` — polygon zone state machine  
- `ENABLE_FIRE_SMOKE` — fire/smoke branch (requires `perception-node/models/fire_smoke.onnx`)  
- `FIRE_SMOKE_MODEL_PATH` — override model location if needed  

### Production hardening checklist

1. **Secrets:** rotate `JWT_SECRET`, database passwords, MinIO keys, and dashboard admin passwords; never commit `.env`.
2. **Transport:** terminate **TLS** at a reverse proxy (or cloud LB) in front of the dashboard and API; use `MINIO_SECURE=true` and proper endpoints when applicable.
3. **Logs:** set `LOG_FORMAT=json` for backend and nodes to feed your log stack.
4. **Postgres:** managed DB or backups + PITR; size for event volume and retention policy.
5. **Object storage:** production MinIO cluster or **S3**-compatible service; tune bucket lifecycle for evidence retention and cost.
6. **Redis:** persistence and HA appropriate to your durability needs for the event stream.
7. **Observability:** keep **Prometheus** scrape configs pointed at every node and the API; alert on FPS drops, ingest lag, and error rates (Grafana dashboards are under `docker/grafana/`).

### Scaling

- **Horizontal:** run **multiple perception nodes** (one per camera or NVR output), each with its own `SOURCE_ID`, writing to the same Redis stream and MinIO bucket prefixing scheme the backend already understands.
- **Vertical:** ONNX can use **CUDA**-capable execution providers where available; adjust `FPS_LIMIT` and `FRAME_SKIP` to meet SLA without overloading CPUs.

Optional **Kubernetes** deployment is not vendored here; the same container images and env vars map cleanly to Deployments (backend), StatefulSets (Postgres/Redis if self-hosted), and DaemonSets or per-camera Jobs for edge inference.

---

## Local development without Docker (optional)

### Infrastructure only

```bash
docker compose -f docker/docker-compose.central.yml up -d
```

Starts Redis, PostgreSQL, and related central pieces (see file for exact services).

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

## Architecture

```
Video input (file or RTSP)
         │
         ▼
 Perception node ──────────────► Redis Stream (vision.events)
         │                                │
         ├── Person + PPE (helmets, vest, gloves)
         ├── Polygon zones (enter / exit)
         ├── Fire / smoke (optional ONNX model)
         ├── ByteTrack
         └── Evidence clips ──► MinIO
                                       │
                                       ▼
                            Central backend
                            ├── Persist events (PostgreSQL)
                            ├── Notifications
                            └── REST / SSE API
                                       │
                                       ▼
                            Next.js dashboard
                            (alerts, analytics, zones, reports)

 Prometheus ◄── scrape /metrics (backend + edge)
      │
      ▼
 Grafana
```

---

## Environment variables (overview)

Important keys (full list in `.env.example`):

```env
# Perception
INPUT_STREAM=/path/or/rtsp://...
SOURCE_ID=camera-01
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
ENABLE_FIRE_SMOKE=true   # when false: no fire/smoke events (inference still runs if model loads)

# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/mvision
JWT_SECRET=change-me-in-production
LOG_FORMAT=text          # json in production
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

End-to-end checks: Redis stream activity, PostgreSQL persistence, MinIO clips, API health, and `/metrics` on backend and perception node.

---

## Documentation and demos

- **[DEMO.md](DEMO.md)** — step-by-step walkthrough (dashboard, API, Grafana, MinIO, acceptance script).

---

## Troubleshooting

**Port conflicts**

```bash
docker compose -f docker/docker-compose.dev.yml down
docker compose -f docker/docker-compose.dev.yml up --build
```

**No events from perception**

- Confirm `INPUT_STREAM` path exists in the container or RTSP is reachable.
- Inspect logs: `docker compose -f docker/docker-compose.dev.yml logs -f perception-node`
- If startup fails loading ONNX, confirm `perception-node/models/fire_smoke.onnx` and `ppe_detector.onnx` / `yolov8n.onnx` are present in the image or mounted path.

**Fresh volumes**

```bash
docker compose -f docker/docker-compose.dev.yml down -v
```

---

## Project structure

```
manufacturing-vision-mvp/
├── .env.example
├── docker/
│   ├── docker-compose.dev.yml    # Full stack
│   ├── docker-compose.central.yml
│   ├── docker-compose.edge.yml
│   ├── prometheus/
│   └── grafana/
├── central-backend/              # FastAPI service
├── perception-node/              # ONNX edge inference
├── frontend-dashboard/           # Next.js UI
├── data/
│   ├── mock_videos/
│   └── volumes/
├── docs/
│   └── phases/                   # Phase plans (e.g. fire/smoke model)
└── tools/
    └── run_acceptance.sh
```
