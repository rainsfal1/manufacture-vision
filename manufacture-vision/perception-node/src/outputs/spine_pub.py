import time
import redis
import json
from typing import Dict, Any
from loguru import logger

from config.settings import settings

class SpinePublisher:
    """
    Publishes JSON events to the internal Redis Streams spine.
    Implements outage policy: drop and log without blocking the main pipeline.

    Zone-level cooldown prevents duplicate events (same source/zone/type) within
    a rolling wall-clock window — this catches track-ID churn on video loops and
    any upstream state-machine gaps.
    """

    # Per-event-type cooldown in seconds (wall clock, not video PTS)
    _COOLDOWN_S: dict[str, float] = {
        "ZONE_ENTER":    30.0,
        "ZONE_EXIT":      5.0,
        "PPE_VIOLATION": 30.0,
        "FIRE_DETECTED": 30.0,
        "SMOKE_DETECTED":30.0,
    }
    _DEFAULT_COOLDOWN_S = 30.0

    def __init__(self):
        self.client = None
        self.stream_name = settings.REDIS_STREAM_NAME
        self.dropped_events = 0
        # (source_id, zone_id, event_type) → last published wall-clock time (seconds)
        self._last_published: dict[tuple, float] = {}
        try:
            self.client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis on startup: {e}")
            self.client = None

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """
        Validates event structure minimally and adds to Redis Stream.

        Zone-level wall-clock cooldown is checked first. Events from the same
        (source, zone, type) tuple within the cooldown window are suppressed here
        so they never reach Redis — this is the last line of defence against
        track-ID churn caused by video loops or brief tracker drops.
        """
        source_id = payload.get("source_id", settings.SOURCE_ID)
        zone_id   = payload.get("zone_id", "unknown")
        dedup_key = (source_id, zone_id, event_type)
        cooldown  = self._COOLDOWN_S.get(event_type, self._DEFAULT_COOLDOWN_S)
        now       = time.monotonic()

        last = self._last_published.get(dedup_key, 0.0)
        if now - last < cooldown:
            logger.debug(
                f"SpinePublisher: suppressed {event_type} for {zone_id} "
                f"(cooldown {cooldown:.0f}s, elapsed {now - last:.1f}s)"
            )
            return

        self._last_published[dedup_key] = now

        event = {
            "schema_version": "1.0",
            "event_type": event_type,
            "event_ts_ms": payload.get("event_ts_ms", 0.0),
            "source_id": payload.get("source_id", settings.SOURCE_ID),
            "track_id": payload.get("track_id", -1),
            "zone_id": payload.get("zone_id", "unknown"),
            "confidence": payload.get("confidence", 100.0),
            "bbox": str(payload.get("bbox", [])),
        }

        # PPE_VIOLATION extra fields
        if event_type == "PPE_VIOLATION":
            event["missing_ppe"] = str(payload.get("missing_ppe", []))
            event["required_ppe"] = str(payload.get("required_ppe", []))

        # Fire/Smoke extra fields
        if event_type in ("FIRE_DETECTED", "SMOKE_DETECTED"):
            event["missing_ppe"] = payload.get("detection_class", "")
            event["confidence"] = float(payload.get("frame_confidence", 0.0))

        # Evidence clip reference (Phase 3)
        if "clip_ref" in payload:
            event["clip_ref"] = payload["clip_ref"]

        if self.client:
            try:
                self.client.xadd(self.stream_name, event)
                logger.info(f"Published {event_type} event to {self.stream_name}")
            except redis.ConnectionError as e:
                self.dropped_events += 1
                logger.error(f"Redis disconnected. Dropped {event_type} event. Total dropped: {self.dropped_events}")
        else:
            self.dropped_events += 1
            logger.error(f"Redis down. Dropped {event_type} event. Total dropped: {self.dropped_events}")
