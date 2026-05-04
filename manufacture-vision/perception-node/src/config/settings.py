import os
from pydantic_settings import BaseSettings

# Base dir is the root of the 'manufacturing-vision-mvp' folder
# settings.py is in perception-node/src/config/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Settings(BaseSettings):
    # Core
    # data/ is in the root
    INPUT_STREAM: str = os.path.join(BASE_DIR, "data/mock_videos/ppe/clip1.mp4")
    SOURCE_ID: str = "camera-01"
    FPS_LIMIT: int = 15
    FRAME_SKIP: int = 3  # Process 1 out of every N frames (reduces CPU load for multi-node demos)
    # Camera Duties
    ENABLE_ZONE_INTRUSION: bool = True
    ENABLE_PPE_COMPLIANCE: bool = True
    ENABLE_FIRE_SMOKE: bool = True

    # Internal Event Spine
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_NAME: str = "vision.events"

    # Zone Configs (This IS inside perception-node)
    ZONES_CONFIG_PATH: str = os.path.join(BASE_DIR, "perception-node/src/config/zones/zones.json")
    
    # Evidence Pipeline (Phase 3)
    MINIO_ENDPOINT:   str   = "localhost:9000"
    MINIO_ACCESS_KEY: str   = "minioadmin"
    MINIO_SECRET_KEY: str   = "minioadmin"
    MINIO_BUCKET:     str   = "vision-evidence"
    MINIO_SECURE:     bool  = False

    RING_BUFFER_RETENTION_S: int   = 30
    CLIP_PRE_EVENT_S:        float = 5.0
    CLIP_POST_EVENT_S:       float = 5.0
    LOW_RES_WIDTH:           int   = 416  # Reduced from 640 to lower CPU for multi-node

    # PPE Detection (Phase 2)
    PPE_MODEL_PATH: str = os.path.join(BASE_DIR, "perception-node/models/ppe_detector.onnx")
    PPE_CONF_THRESH: float = 0.25
    PPE_VIOLATION_HYSTERESIS: int = 2    # consecutive frames required before firing (lowered for multi-node demo)
    PPE_VIOLATION_COOLDOWN_MS: float = 30_000  # 30s cooldown between re-fires

    # Fire/Smoke Detection (Phase 14)
    FIRE_SMOKE_MODEL_PATH: str = os.path.join(BASE_DIR, "perception-node/models/fire_smoke.onnx")
    FIRE_SMOKE_CONF_THRESH: float = 0.4
    FIRE_SMOKE_HYSTERESIS: int = 2       # lowered for multi-node demo
    FIRE_SMOKE_COOLDOWN_MS: float = 30_000   # 30s for demo (was 5 min)
    FIRE_SMOKE_PRE_EVENT_S: float = 10.0

    # Central Backend (Phase 6) — set to pull zone config at startup
    BACKEND_URL: str = ""  # e.g. http://localhost:8000; empty = disabled

    # Observability
    METRICS_PORT: int = 9091
    LOG_FORMAT: str = "text"  # "text" | "json"

    # Debug
    DEBUG_OVERLAY: bool = True
    DEBUG_OUTPUT_PATH: str = os.path.join(BASE_DIR, "perception-node/debug_output.mp4")

    class Config:
        env_file = ".env"

settings = Settings()
