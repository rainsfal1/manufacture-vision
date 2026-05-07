import sys
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.media import router as media_router
from app.api.zones import router as zones_router
from app.api.policies import router as policies_router
from app.api.reports import router as reports_router
from app.api.notifications import router as notifications_router
from app.api.demo import router as demo_router
from app.core.config import settings
from app.core.database import engine
from app.services import event_consumer, notification_dispatcher

if settings.LOG_FORMAT == "json":
    logger.remove()
    logger.add(sys.stdout, serialize=True, level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify database is reachable
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Start Redis consumer as daemon thread
    t = threading.Thread(target=event_consumer.run, daemon=True, name="event-consumer")
    t.start()
    logger.info("Event consumer thread started")

    # Start notification dispatcher as daemon thread
    nd = threading.Thread(target=notification_dispatcher.run, daemon=True, name="notif-dispatcher")
    nd.start()
    logger.info("Notification dispatcher thread started")

    yield
    # Daemon thread exits with the process — no explicit cleanup needed


app = FastAPI(title="manufacture-vision backend", version="1.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(media_router, prefix="/media", tags=["media"])
app.include_router(zones_router, prefix="/zones", tags=["zones"])
app.include_router(policies_router, prefix="/policies", tags=["policies"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
app.include_router(demo_router, prefix="/demo", tags=["demo"])


@app.get("/health", tags=["health"])
def health():
    return {
        "title": "Central Backend Operational Status",
        "service": "manufacture-vision",
        "status": "ok"
    }
