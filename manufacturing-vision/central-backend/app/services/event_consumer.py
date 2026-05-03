import json
import time

import redis as redis_lib
from loguru import logger
from prometheus_client import Counter

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.event import Event

backend_events_ingested = Counter("backend_events_ingested_total", "Events consumed from Redis")

# Backend-side dedup: (source_id, zone_id, event_type) → last persisted wall-clock time.
# This is a second line of defence in case the perception node sends duplicates
# (e.g. two nodes running the same camera, or a perception restart mid-clip).
_DEDUP_COOLDOWN_S: dict[str, float] = {
    "ZONE_ENTER":     30.0,
    "ZONE_EXIT":       5.0,
    "PPE_VIOLATION":  30.0,
    "FIRE_DETECTED":  30.0,
    "SMOKE_DETECTED": 30.0,
}
_DEFAULT_COOLDOWN_S = 30.0
_last_persisted: dict[tuple, float] = {}


def run() -> None:
    r = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Create consumer group — ignore error if it already exists
    try:
        r.xgroup_create(settings.REDIS_STREAM_NAME, settings.REDIS_CONSUMER_GROUP,
                        id="0", mkstream=True)
        logger.info(f"EventConsumer: created group '{settings.REDIS_CONSUMER_GROUP}'")
    except redis_lib.ResponseError:
        logger.info(f"EventConsumer: group '{settings.REDIS_CONSUMER_GROUP}' already exists")

    logger.info("EventConsumer: started, listening on vision.events")

    while True:
        try:
            messages = r.xreadgroup(
                settings.REDIS_CONSUMER_GROUP,
                settings.REDIS_CONSUMER_NAME,
                {settings.REDIS_STREAM_NAME: ">"},
                count=10,
                block=1000,
            )
            for _stream, entries in (messages or []):
                for msg_id, fields in entries:
                    try:
                        if _is_duplicate(fields):
                            # ACK so it doesn't re-deliver, but don't persist or broadcast
                            r.xack(settings.REDIS_STREAM_NAME,
                                   settings.REDIS_CONSUMER_GROUP, msg_id)
                            continue

                        event_id = _persist(fields)
                        fields["id"] = event_id
                        r.xack(settings.REDIS_STREAM_NAME,
                               settings.REDIS_CONSUMER_GROUP, msg_id)
                        logger.debug(f"EventConsumer: persisted {fields.get('event_type')} [{msg_id}]")
                        try:
                            r.publish("vision.events.broadcast", json.dumps(fields))
                        except Exception as pub_err:
                            logger.warning(f"EventConsumer: pub/sub publish failed: {pub_err}")
                    except Exception as e:
                        logger.error(f"EventConsumer: failed to persist {msg_id}: {e}")
                        # Do not XACK — message stays in PEL for redelivery
        except redis_lib.ConnectionError as e:
            logger.error(f"EventConsumer: Redis connection lost: {e} — retrying in 2s")
            time.sleep(2)
        except Exception as e:
            logger.error(f"EventConsumer: unexpected error: {e}")
            time.sleep(1)


def _is_duplicate(fields: dict) -> bool:
    event_type = fields.get("event_type", "UNKNOWN")
    key = (fields.get("source_id", ""), fields.get("zone_id", ""), event_type)
    cooldown = _DEDUP_COOLDOWN_S.get(event_type, _DEFAULT_COOLDOWN_S)
    now = time.monotonic()
    last = _last_persisted.get(key, 0.0)
    if now - last < cooldown:
        logger.info(
            f"EventConsumer: dedup suppressed {event_type} for {key[1]} "
            f"(elapsed {now - last:.1f}s < {cooldown:.0f}s)"
        )
        return True
    _last_persisted[key] = now
    return False


def _persist(fields: dict) -> int:
    with SessionLocal() as db:
        event = Event(
            event_type=fields.get("event_type", "UNKNOWN"),
            event_ts_ms=int(float(fields.get("event_ts_ms", 0))),
            source_id=fields.get("source_id"),
            track_id=int(fields["track_id"]) if fields.get("track_id") else None,
            zone_id=fields.get("zone_id"),
            confidence=float(fields["confidence"]) if fields.get("confidence") else None,
            bbox=fields.get("bbox"),
            missing_ppe=fields.get("missing_ppe"),
            clip_ref=fields.get("clip_ref"),
        )
        db.add(event)
        db.commit()
        backend_events_ingested.inc()
        return event.id
