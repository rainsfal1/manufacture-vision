# Central Backend

RESTful API server for event management, configuration, and system orchestration. Built with FastAPI and PostgreSQL.

## Overview

The Central Backend serves as the core API layer for Manufacture Vision, providing:

- Event storage and retrieval with rich filtering
- Zone and policy management
- User authentication and role-based access control
- Analytics and compliance reporting
- Evidence clip access with secure signed URLs
- Real-time alert notifications
- System health monitoring

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 16 (or Docker)
- Redis 7 (or Docker)
- MinIO (or Docker)

### Installation

```bash
# Install dependencies
uv sync

# Create .env file
cp ../.env.example .env

# Run database migrations
python -m alembic upgrade head

# Start development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at: http://localhost:8000

### Docker

Start with all dependencies:

```bash
docker-compose -f ../docker/docker-compose.central.yml up
```

Then run:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://mvision:mvision@localhost:5432/mvision
SQLALCHEMY_ECHO=false
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_POOL_TIMEOUT=30

# Authentication
JWT_SECRET=your-secret-key-min-32-characters
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256

# Initial Admin
ADMIN_USER=admin
ADMIN_PASSWORD=admin

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_STREAM_NAME=vision.events
REDIS_BATCH_SIZE=100
REDIS_CONSUMER_GROUP=central-backend

# MinIO (S3-compatible)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vision-evidence
MINIO_SECURE=false

# API
API_TITLE=Manufacture Vision API
API_VERSION=1.0.0
API_DESCRIPTION=Real-time manufacturing safety monitoring
DEBUG=false

# Notifications
NOTIFICATION_ENABLED=true
NOTIFICATION_WORKERS=4
SSE_HEARTBEAT_INTERVAL=30
```

### Database Setup

Initialize database:

```bash
python -m alembic upgrade head
```

Create custom migration:

```bash
python -m alembic revision --autogenerate -m "Description"
python -m alembic upgrade head
```

View migration history:

```bash
python -m alembic history
```

Downgrade:

```bash
python -m alembic downgrade -1
```

## API Documentation

### Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Authentication

All endpoints (except `/auth/login`) require a valid JWT token in the `Authorization` header:

```bash
Authorization: Bearer <token>
```

Obtain token via login:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

Response:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Endpoints

#### Authentication

**POST /auth/login**

Authenticate user and receive JWT token.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d {
    "username": "admin",
    "password": "admin"
  }
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### System Health

**GET /health**

Check system health status.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-04-29T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "minio": "connected"
  }
}
```

#### Events

**GET /events**

Query events with filtering, sorting, and pagination.

```bash
curl "http://localhost:8000/events?event_type=ppe_violation&limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Query Parameters:
- `event_type` - Filter by event type (ppe_violation, intrusion, fire, etc.)
- `source_id` - Filter by camera/source ID
- `start_time` - ISO 8601 timestamp
- `end_time` - ISO 8601 timestamp
- `zone_id` - Filter by zone
- `limit` - Results per page (default: 20, max: 100)
- `offset` - Pagination offset (default: 0)
- `sort` - Sort field (timestamp, severity; default: -timestamp)

Response:
```json
{
  "total": 245,
  "events": [
    {
      "id": "evt-123",
      "type": "ppe_violation",
      "severity": "high",
      "source_id": "camera-01",
      "zone_id": "zone-assembly",
      "timestamp": "2024-04-29T10:25:30Z",
      "description": "Worker missing helmet in assembly area",
      "metadata": {
        "person_id": "track-456",
        "missing_ppe": ["helmet"],
        "confidence": 0.95
      },
      "evidence_clip": {
        "clip_id": "clip-789",
        "duration_ms": 10000,
        "created_at": "2024-04-29T10:25:30Z"
      }
    }
  ]
}
```

**GET /events/{event_id}**

Get detailed event information.

```bash
curl http://localhost:8000/events/evt-123 \
  -H "Authorization: Bearer $TOKEN"
```

**POST /events**

Create new event (typically for edge node publishing).

```bash
curl -X POST http://localhost:8000/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "type": "ppe_violation",
    "source_id": "camera-01",
    "zone_id": "zone-assembly",
    "severity": "high",
    "metadata": {
      "person_id": "track-456",
      "missing_ppe": ["helmet"]
    }
  }
```

#### Media/Evidence

**GET /media/{event_id}**

Get signed URL to evidence clip.

```bash
curl http://localhost:8000/media/evt-123 \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "clip_id": "clip-789",
  "url": "http://localhost:9000/vision-evidence/clip-789.mp4?X-Amz-Signature=...",
  "duration_ms": 10000,
  "created_at": "2024-04-29T10:25:30Z",
  "expires_in_seconds": 3600
}
```

#### Zones

**GET /zones**

List all detection zones.

```bash
curl http://localhost:8000/zones \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "zones": [
    {
      "id": "zone-assembly",
      "name": "Assembly Area",
      "description": "Main assembly line",
      "polygon": [
        {"x": 0, "y": 0},
        {"x": 100, "y": 0},
        {"x": 100, "y": 100},
        {"x": 0, "y": 100}
      ],
      "policies": {
        "ppe_required": ["helmet", "vest"],
        "max_occupancy": 10,
        "restricted_hours": {
          "start": "22:00",
          "end": "06:00"
        }
      },
      "created_at": "2024-04-29T00:00:00Z",
      "updated_at": "2024-04-29T10:00:00Z"
    }
  ]
}
```

**GET /zones/{zone_id}**

Get zone details.

```bash
curl http://localhost:8000/zones/zone-assembly \
  -H "Authorization: Bearer $TOKEN"
```

**POST /zones**

Create new zone.

```bash
curl -X POST http://localhost:8000/zones \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "name": "Painting Area",
    "description": "Paint station with PPE requirements",
    "polygon": [
      {"x": 150, "y": 0},
      {"x": 250, "y": 0},
      {"x": 250, "y": 100},
      {"x": 150, "y": 100}
    ],
    "policies": {
      "ppe_required": ["helmet", "vest", "gloves"],
      "max_occupancy": 5
    }
  }
```

**PUT /zones/{zone_id}**

Update zone configuration.

```bash
curl -X PUT http://localhost:8000/zones/zone-assembly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "name": "Assembly Area (Updated)",
    "policies": {
      "ppe_required": ["helmet", "vest"]
    }
  }
```

**DELETE /zones/{zone_id}**

Delete zone.

```bash
curl -X DELETE http://localhost:8000/zones/zone-assembly \
  -H "Authorization: Bearer $TOKEN"
```

#### Policies

**GET /policies**

List all safety policies.

```bash
curl http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN"
```

**POST /policies**

Create new policy.

```bash
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "name": "Standard PPE",
    "description": "Minimum PPE for assembly areas",
    "requirements": {
      "helmet": true,
      "vest": true,
      "gloves": false
    }
  }
```

#### Reports

**GET /reports/compliance**

Get compliance metrics and trends.

```bash
curl "http://localhost:8000/reports/compliance?start_date=2024-04-01&end_date=2024-04-30" \
  -H "Authorization: Bearer $TOKEN"
```

Query Parameters:
- `start_date` - Start date (ISO 8601)
- `end_date` - End date (ISO 8601)
- `zone_id` - Optional zone filter
- `group_by` - Group results (day, week, month)

Response:
```json
{
  "period": {
    "start": "2024-04-01T00:00:00Z",
    "end": "2024-04-30T23:59:59Z"
  },
  "summary": {
    "total_events": 1542,
    "compliance_rate": 0.92,
    "violations_by_type": {
      "ppe_violation": 89,
      "intrusion": 45,
      "restricted_access": 23
    }
  },
  "zones": [
    {
      "zone_id": "zone-assembly",
      "zone_name": "Assembly Area",
      "events": 892,
      "compliance_rate": 0.94,
      "most_common_violation": "missing_helmet"
    }
  ],
  "daily_trends": [
    {
      "date": "2024-04-29",
      "events": 89,
      "compliance_rate": 0.91
    }
  ]
}
```

**GET /reports/incidents**

Detailed incident analysis.

```bash
curl "http://localhost:8000/reports/incidents?severity=high&start_date=2024-04-01" \
  -H "Authorization: Bearer $TOKEN"
```

#### Notifications

**GET /notifications/live**

Server-Sent Events (SSE) stream for real-time alerts.

```bash
curl http://localhost:8000/notifications/live \
  -H "Authorization: Bearer $TOKEN"
```

Subscribes to real-time event stream. Events are sent as they occur:

```
data: {"event_id":"evt-123","type":"ppe_violation","severity":"high"}
data: {"event_id":"evt-124","type":"intrusion","severity":"critical"}
```

**GET /notifications**

Get recent notifications.

```bash
curl "http://localhost:8000/notifications?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**POST /notifications/webhook**

Register webhook for external notifications.

```bash
curl -X POST http://localhost:8000/notifications/webhook \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "url": "https://your-service.com/alerts",
    "event_types": ["ppe_violation", "intrusion"],
    "severity_filter": ["high", "critical"]
  }
```

## Architecture

### Directory Structure

```
central-backend/
├── app/
│   ├── main.py                 # FastAPI application setup
│   ├── api/
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── events.py           # Event query/management
│   │   ├── media.py            # Evidence clip endpoints
│   │   ├── zones.py            # Zone management
│   │   ├── policies.py         # Policy management
│   │   ├── reports.py          # Analytics endpoints
│   │   ├── notifications.py    # Alert endpoints
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── security.py         # JWT & RBAC utilities
│   │   └── __init__.py
│   ├── models/
│   │   ├── event.py            # Event ORM model
│   │   ├── zone.py             # Zone ORM model
│   │   ├── policy.py           # Policy ORM model
│   │   ├── user.py             # User ORM model
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── event.py            # Event Pydantic schema
│   │   ├── zone.py             # Zone Pydantic schema
│   │   ├── auth.py             # Auth Pydantic schema
│   │   └── __init__.py
│   ├── services/
│   │   ├── event_consumer.py   # Redis stream consumer
│   │   ├── notification_dispatcher.py
│   │   ├── storage.py          # MinIO operations
│   │   └── __init__.py
│   ├── integrations/
│   │   ├── redis.py            # Redis client
│   │   ├── minio.py            # MinIO client
│   │   └── __init__.py
│   ├── migrations/             # Alembic migration folder
│   └── __init__.py
├── pyproject.toml              # Dependencies
├── alembic.ini                 # Migration config
├── main.py                     # Entry point
├── Dockerfile                  # Container image
└── README.md                   # This file
```

### Key Components

**FastAPI Application** (`app/main.py`)
- Creates FastAPI instance
- Mounts API routers
- Configures CORS
- Sets up middleware (logging, error handling)
- Implements health check

**Database Layer**
- SQLAlchemy ORM with PostgreSQL
- Alembic migrations
- Connection pooling
- Query optimization

**Authentication**
- JWT token generation and validation
- Role-based access control (RBAC)
- Password hashing with bcrypt

**Event Consumer**
- Redis Streams consumer group
- Processes events from perception nodes
- Stores to PostgreSQL
- Publishes to SSE subscribers

**Storage**
- MinIO S3-compatible client
- Signed URL generation
- Clip lifecycle management

## Development

### Run with Hot Reload

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_auth.py::test_login
```

### Database Operations

Create migration:

```bash
alembic revision --autogenerate -m "Add new table"
```

Apply migrations:

```bash
alembic upgrade head
```

View current schema:

```bash
psql $DATABASE_URL -c "\dt"
```

### Code Quality

Format code:

```bash
black app/
isort app/
```

Type checking:

```bash
mypy app/
```

Linting:

```bash
ruff check app/
```

## Production Deployment

### Docker Build

```bash
docker build -t manufacture-vision-backend:latest .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e JWT_SECRET="..." \
  -e REDIS_URL="..." \
  manufacture-vision-backend:latest
```

### Environment Variables

Set all environment variables before running:

```bash
export DATABASE_URL="postgresql://mvision:password@prod-db:5432/mvision"
export JWT_SECRET="$(openssl rand -hex 32)"
export REDIS_URL="redis://prod-redis:6379/0"
export MINIO_ENDPOINT="s3.example.com"
export ADMIN_USER="admin"
export ADMIN_PASSWORD="$(openssl rand -base64 32)"
```

### Database Migration

On deployment, always run migrations:

```bash
python -m alembic upgrade head
```

### Monitoring

Health check endpoint for load balancers:

```bash
GET /health
```

Prometheus metrics (if configured):

```bash
GET /metrics
```

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

Check connection string:

```bash
psql $DATABASE_URL
```

Verify PostgreSQL is running:

```bash
docker ps | grep postgres
```

### JWT Token Errors

Invalid token:

```json
{"detail": "Invalid authentication credentials"}
```

Ensure:
1. Token is passed in Authorization header
2. Token format: `Bearer <token>`
3. Token not expired (check `JWT_EXPIRE_HOURS`)
4. JWT_SECRET matches across all instances

### Redis Connection Issues

```
redis.exceptions.ConnectionError: Error -2 connecting to localhost:6379
```

Check Redis is running:

```bash
redis-cli ping
```

Verify REDIS_URL:

```bash
echo $REDIS_URL
```

### MinIO Upload Errors

Ensure MinIO is running and bucket exists:

```bash
docker exec minio mc ls minio/vision-evidence
```

Check credentials in .env match MinIO container settings.

## Performance Optimization

### Database Tuning

```env
# Connection pooling
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_POOL_TIMEOUT=30

# Query optimization
SQLALCHEMY_ECHO=false  # Disable in production
```

Add indexes:

```sql
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_source_id ON events(source_id);
CREATE INDEX idx_events_zone_id ON events(zone_id);
CREATE INDEX idx_events_type ON events(event_type);
```

### Cache Strategy

Frequently accessed data in Redis:

- Zone configurations
- Policy definitions
- User sessions

### Pagination

Always paginate large result sets:

```bash
curl "http://localhost:8000/events?limit=100&offset=0"
```

Default limit: 20, Max limit: 100

## Support

For additional help:

1. Check logs: `docker logs central-backend`
2. Review API docs: http://localhost:8000/docs
3. Check database: `psql $DATABASE_URL`
4. Verify Redis: `redis-cli -u $REDIS_URL`

## License

Proprietary - All rights reserved
