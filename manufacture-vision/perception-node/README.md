# Perception Node

Real-time edge AI inference engine for manufacturing safety monitoring. Runs video analysis locally without cloud dependency.

## Overview

The Perception Node is the edge computing component of Manufacture Vision. It:

- Ingests video streams (MP4 files, RTSP cameras)
- Performs real-time AI inference using ONNX models
- Detects persons, PPE, and anomalies
- Tracks individuals across frames with ByteTrack
- Generates safety events based on spatial analysis
- Captures evidence clips with pre/post-event retention
- Publishes events to central backend via Redis

Key advantages:
- No cloud upload required (factory IP protection)
- Sub-100ms latency for critical alerts
- Works with poor network connectivity
- Scales to multiple cameras
- Supports diverse video input formats

## Quick Start

### Prerequisites

- Python 3.13+
- 2GB+ RAM (4GB+ recommended)
- 2+ CPU cores
- NVIDIA GPU optional (10x+ faster with CUDA)

### Installation

```bash
# Install dependencies
uv sync

# Create .env file
cp ../.env.example .env

# Start inference (make sure infrastructure is running first)
uv run python src/main.py
```

Or with Docker:

```bash
docker-compose -f ../docker/docker-compose.edge.yml up --build
```

## Configuration

### Environment Variables

```env
# Video Input
SOURCE_ID=camera-01
INPUT_STREAM=data/mock_videos/ppe/clip1.mp4
FPS_LIMIT=15
FRAME_SKIP=0

# Processing
LOW_RES_WIDTH=640
LOW_RES_HEIGHT=480
HIGH_RES_WIDTH=1280
HIGH_RES_HEIGHT=720

# Detection Models
PERSON_DETECTION_MODEL=models/yolov8n.onnx
PPE_DETECTION_MODEL=models/ppe_detector.onnx
DETECTION_CONF_THRESHOLD=0.5

# PPE Detection
PPE_CONF_THRESH=0.4
PPE_CLASSES=helmet,vest,gloves
PPE_VIOLATION_HYSTERESIS=3
PPE_VIOLATION_COOLDOWN_MS=30000

# Evidence Pipeline
RING_BUFFER_RETENTION_S=30
CLIP_PRE_EVENT_S=5.0
CLIP_POST_EVENT_S=5.0
EVIDENCE_CODEC=h264
EVIDENCE_BITRATE=5000k

# Tracking
TRACKER_TYPE=bytetrack
TRACK_HIGH_THRESH=0.7
TRACK_LOW_THRESH=0.1
TRACK_NEW_THRESH=0.7
TRACK_BUFFER_SIZE=30

# Backend Integration
BACKEND_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379/0
REDIS_STREAM_NAME=vision.events

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vision-evidence
MINIO_SECURE=false

# Telemetry
TELEMETRY_ENABLED=true
TELEMETRY_INTERVAL_S=10
LOG_LEVEL=INFO
DEBUG=false
```

### Zone Configuration

Define detection zones in JSON format:

```json
{
  "zones": [
    {
      "id": "zone-assembly",
      "name": "Assembly Area",
      "type": "danger_zone",
      "polygon": [
        {"x": 0, "y": 0},
        {"x": 640, "y": 0},
        {"x": 640, "y": 480},
        {"x": 0, "y": 480}
      ],
      "policies": {
        "ppe_required": ["helmet", "vest"],
        "restricted_hours": {"start": "22:00", "end": "06:00"},
        "max_occupancy": 10
      }
    },
    {
      "id": "zone-office",
      "name": "Office Area",
      "type": "restricted",
      "polygon": [
        {"x": 640, "y": 0},
        {"x": 1280, "y": 0},
        {"x": 1280, "y": 240},
        {"x": 640, "y": 240}
      ],
      "policies": {
        "restricted": true
      }
    }
  ]
}
```

Load zones from backend:

```bash
# Perception node will fetch zones from backend on startup
BACKEND_URL=http://localhost:8000
```

Or use local zones file:

```bash
ZONES_FILE=zones.json
```

## Architecture

### Data Flow Pipeline

```
┌─────────────────────┐
│  Video Source       │
│  (MP4/RTSP)         │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Frame Ingestion    │
│  (PyAV Reader)      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Bounded Buffer     │
│  (Backpressure)     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │            │
┌────▼────┐  ┌──▼──────┐
│ Low-Res │  │High-Res  │
│(Infer)  │  │(Evidence)│
└────┬────┘  └──┬───────┘
     │          │
┌────▼──────────▼────┐
│ Detection (ONNX)   │
│ Person + PPE       │
└────┬───────────────┘
     │
┌────▼──────────────┐
│ Tracking          │
│ (ByteTrack)       │
└────┬──────────────┘
     │
┌────▼──────────────┐
│ Spatial Analysis  │
│ (Polygon Zones)   │
└────┬──────────────┘
     │
┌────▼──────────────┐
│ Event Generation  │
│ (State Machine)   │
└────┬──────────────┘
     │
┌────▼──────────────┐
│ Evidence Capture  │
│ (Ring Buffer)     │
└────┬──────────────┘
     │
┌────▼──────────────┐
│ Publishing        │
│ (Redis Streams)   │
└───────────────────┘
```

### Module Structure

```
perception-node/
├── src/
│   ├── main.py                 # Entry point & event loop
│   ├── config/
│   │   ├── settings.py         # Pydantic configuration
│   │   └── zones.py            # Zone configuration loader
│   ├── detection/
│   │   ├── onnx_runner.py      # ONNX model inference
│   │   └── ppe_detector.py     # PPE classification
│   ├── ingestion/
│   │   ├── reader.py           # PyAV video reader
│   │   ├── frame_buffer.py     # Bounded queue
│   │   └── dual_stream.py      # Low/high-res fork
│   ├── tracking/
│   │   └── bytetrack.py        # Multi-object tracking
│   ├── spatial/
│   │   └── geometry.py         # Polygon & point-in-polygon
│   ├── rules/
│   │   ├── state_machine.py    # Entry/exit state machine
│   │   ├── ppe_policy.py       # PPE compliance
│   │   ├── policies.py         # Policy engine
│   │   └── debouncer.py        # Hysteresis & cooldown
│   ├── evidence/
│   │   ├── ring_buffer.py      # Circular frame buffer
│   │   ├── exporter.py         # MP4 clip export
│   │   ├── s3_uploader.py      # MinIO upload
│   │   └── worker.py           # Evidence thread
│   ├── outputs/
│   │   └── spine_pub.py        # Redis stream publisher
│   ├── telemetry/
│   │   └── monitor.py          # Metrics & health
│   └── utils/
│       ├── logger.py           # Structured logging
│       └── timing.py           # Performance profiling
├── models/
│   ├── yolov8n.onnx            # Person detection
│   └── ppe_detector.onnx       # PPE classification
├── pyproject.toml              # Dependencies
├── main.py                     # Wrapper entry point
├── Dockerfile                  # Container image
└── README.md                   # This file
```

### Running

#### With Mock Video

```bash
# Use provided test video
export INPUT_STREAM=../data/mock_videos/ppe/clip1.mp4
uv run python src/main.py
```

#### With RTSP Camera

```bash
# Real-time camera stream
export INPUT_STREAM=rtsp://192.168.1.100:554/stream1
uv run python src/main.py
```

#### With Custom Video File

```bash
# Point to any video file
export INPUT_STREAM=/path/to/video.mp4
uv run python src/main.py
```

### With Docker

```bash
docker build -t perception-node:latest .
docker run -it \
  -v $(pwd)/data:/app/data \
  -e INPUT_STREAM=/app/data/video.mp4 \
  -e BACKEND_URL=http://host.docker.internal:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  perception-node:latest
```

## Inference Performance

### Speed (CPU)

- YOLOv8n person detection: 30-50 FPS @ 640x480
- PPE classification: 50+ FPS @ 64x64 crop
- ByteTrack: 100+ FPS
- Overall pipeline: 15-25 FPS

### Speed (GPU - NVIDIA CUDA)

- YOLOv8n person detection: 100+ FPS @ 640x480
- PPE classification: 200+ FPS @ 64x64 crop
- ByteTrack: 300+ FPS
- Overall pipeline: 50-100 FPS

### Memory Usage

- Base: ~500 MB
- With models: ~1.5 GB
- Ring buffer (30s @ 720p): ~2.5 GB
- Total: ~4.5 GB typical

### Optimization Tips

Reduce CPU usage:

```env
FPS_LIMIT=10          # Process fewer frames
LOW_RES_WIDTH=480     # Smaller inference resolution
FRAME_SKIP=2          # Process every 2nd frame
```

Enable GPU acceleration:

```bash
# Install CUDA toolkit first
pip install onnxruntime-gpu
export ONNXRUNTIME_GPU=1
```

Reduce memory:

```env
RING_BUFFER_RETENTION_S=15  # Shorter evidence buffer
FRAME_BUFFER_SIZE=30         # Smaller frame queue
```

## Model Management

### YOLOv8n (Person Detection)

Pre-trained ONNX model for person detection.

Convert from PyTorch:

```bash
# Install Ultralytics
pip install ultralytics

# Download & export
python -c "from ultralytics import YOLO; m = YOLO('yolov8n.pt'); m.export(format='onnx', imgsz=640)"
```

### PPE Detector (Helmet, Vest, Gloves)

Custom-trained model for PPE classification.

Train your own:

```bash
python tools/export_ppe_model.py \
  --train_dir data/ppe/train \
  --val_dir data/ppe/val \
  --epochs 100 \
  --output models/ppe_detector.onnx
```

## Event Generation

### Zone Entry/Exit

When a person enters a zone:

```json
{
  "event_type": "zone_entry",
  "source_id": "camera-01",
  "zone_id": "zone-assembly",
  "timestamp": "2024-04-29T10:25:30Z",
  "person_id": "track-456",
  "confidence": 0.95
}
```

### PPE Violation

When a person violates PPE policy:

```json
{
  "event_type": "ppe_violation",
  "source_id": "camera-01",
  "zone_id": "zone-assembly",
  "timestamp": "2024-04-29T10:25:35Z",
  "person_id": "track-456",
  "missing_ppe": ["helmet"],
  "confidence": 0.92
}
```

### Restricted Area Intrusion

When a person enters restricted zone:

```json
{
  "event_type": "intrusion",
  "source_id": "camera-01",
  "zone_id": "zone-office",
  "timestamp": "2024-04-29T10:25:40Z",
  "person_id": "track-456",
  "severity": "high"
}
```

## Evidence Capture

When an event is generated, evidence is automatically captured:

1. **Ring Buffer** - Last 30 seconds of video stored in memory
2. **Pre-Event** - 5 seconds before event trigger
3. **Event** - Moment of violation
4. **Post-Event** - 5 seconds after event trigger
5. **Clip Export** - MP4 video with bounding boxes
6. **Upload** - Send to MinIO with metadata
7. **Publish** - Send reference to central backend

Example evidence clip (MP4):

```
clip-789.mp4
  ├── Duration: 10 seconds (5s before + 5s after)
  ├── Resolution: 1280x720
  ├── Codec: H.264
  ├── Bitrate: 5000 kbps
  ├── FPS: 30
  └── Metadata:
      ├── event_id: evt-123
      ├── person_id: track-456
      ├── violation: missing_helmet
      └── timestamp: 2024-04-29T10:25:30Z
```

## Monitoring & Diagnostics

### Health Check

Check if node is running:

```bash
redis-cli XLEN vision.events
```

If increasing, inference is working.

### Performance Metrics

View in logs:

```bash
# FPS, CPU, memory, latency
tail -f node.log | grep METRICS
```

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
DEBUG=true
```

Verbose output:

```bash
python src/main.py --verbose
```

### Stream Validation

Test video input:

```bash
python tools/verify_stream.py --video data/mock_videos/ppe/clip1.mp4
```

Output:

```
Video Stream: data/mock_videos/ppe/clip1.mp4
  Resolution: 1280x720
  FPS: 30
  Duration: 10 seconds
  Codec: h264
  Status: OK
```

### Model Loading

Verify models are loaded:

```bash
python -c "from src.detection.onnx_runner import ONNXRunner; r = ONNXRunner('models/yolov8n.onnx'); print(f'Inputs: {r.input_names}'); print(f'Outputs: {r.output_names}')"
```

## Troubleshooting

### No Events Generated

1. Check video input is loading:
   ```bash
   python tools/verify_stream.py --video $INPUT_STREAM
   ```

2. Check Redis connection:
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

3. Check models are loaded:
   ```bash
   ls -la models/
   ```

4. Enable debug logging and review output:
   ```bash
   LOG_LEVEL=DEBUG python src/main.py
   ```

### High CPU Usage

1. Reduce FPS_LIMIT:
   ```env
   FPS_LIMIT=10
   ```

2. Reduce inference resolution:
   ```env
   LOW_RES_WIDTH=480
   ```

3. Skip frames:
   ```env
   FRAME_SKIP=1
   ```

4. Enable GPU acceleration (if available)

### Memory Leak

1. Check ring buffer size isn't growing indefinitely:
   ```bash
   watch -n 1 'ps aux | grep python | grep perception'
   ```

2. Reduce RING_BUFFER_RETENTION_S:
   ```env
   RING_BUFFER_RETENTION_S=15
   ```

3. Restart node periodically

### Slow Event Publishing

1. Verify Redis is responsive:
   ```bash
   redis-cli --latency
   ```

2. Check network connectivity to backend
3. Reduce batch publish size if needed

### Models Not Loading

1. Verify model files exist:
   ```bash
   ls -la models/*.onnx
   ```

2. Check file permissions:
   ```bash
   chmod 644 models/*.onnx
   ```

3. Validate ONNX format:
   ```bash
   python -c "import onnx; m = onnx.load('models/yolov8n.onnx'); print(onnx.helper.printable_graph(m.graph))"
   ```

4. Check ONNX Runtime version:
   ```bash
   python -c "import onnxruntime; print(onnxruntime.__version__)"
   ```

## Development

### Installation for Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Unit tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Integration tests
pytest tests/integration/
```

### Code Quality

Format:

```bash
black src/ tests/
isort src/ tests/
```

Type checking:

```bash
mypy src/
```

Linting:

```bash
ruff check src/
```

### Profiling

Profile inference:

```bash
python -m cProfile -s cumtime src/main.py 2>&1 | head -20
```

Memory profiling:

```bash
pip install memory-profiler
python -m memory_profiler src/main.py
```

## Production Deployment

### Docker Build & Run

```bash
# Build
docker build -t perception-node:v1.0 .

# Run
docker run -d \
  --name perception-1 \
  --restart unless-stopped \
  -v /mnt/data:/app/data \
  -e SOURCE_ID=camera-01 \
  -e INPUT_STREAM=rtsp://camera:554/stream1 \
  -e BACKEND_URL=http://backend:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  perception-node:v1.0
```

### Multi-Camera Setup

Run separate instances:

```bash
# Camera 1
docker run -d --name perception-1 \
  -e SOURCE_ID=camera-01 \
  -e INPUT_STREAM=rtsp://cam1:554/stream \
  ...

# Camera 2
docker run -d --name perception-2 \
  -e SOURCE_ID=camera-02 \
  -e INPUT_STREAM=rtsp://cam2:554/stream \
  ...
```

### Hardware Optimization

GPU acceleration:

```bash
# Install GPU support
pip install onnxruntime-gpu

# Run with GPU
docker run --gpus all perception-node:v1.0
```

CPU pinning:

```bash
# Use 2 CPU cores
docker run --cpus="2" perception-node:v1.0
```

Memory limit:

```bash
# Limit to 4GB
docker run --memory="4g" perception-node:v1.0
```

## Integration with Backend

The perception node automatically:

1. Fetches zones from backend on startup
2. Publishes events to Redis stream
3. Uploads evidence clips to MinIO
4. Reports health/telemetry periodically

To integrate with a remote backend:

```env
BACKEND_URL=http://your-backend.com:8000
REDIS_URL=redis://your-redis.com:6379/0
MINIO_ENDPOINT=your-minio.com:9000
```

## License

Proprietary - All rights reserved
