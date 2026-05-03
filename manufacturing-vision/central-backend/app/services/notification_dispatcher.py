"""
Notification dispatcher daemon for Phase 9.

Subscribes to vision.events.broadcast (Redis pub/sub), matches each event
against active notification rules, and dispatches to the appropriate channel
driver. Runs as a daemon thread started from app/main.py lifespan.
"""
import json
import threading
import time

import redis as redis_lib
from loguru import logger
from prometheus_client import Counter

from app.core.config import settings

backend_notifications = Counter(
    "backend_notifications_dispatched_total", "Notifications sent", ["channel_type"]
)
from app.core.database import SessionLocal
from app.models.notification_channel import NotificationChannel
from app.models.notification_rule import NotificationRule
from app.services.channel_drivers import get_driver

_REFRESH_INTERVAL = 60  # seconds


class NotificationDispatcher:
    def __init__(self) -> None:
        self._rules: list[tuple[NotificationRule, NotificationChannel]] = []
        self._lock = threading.Lock()

    def _load_rules(self) -> None:
        with SessionLocal() as db:
            rules = (
                db.query(NotificationRule)
                .filter(NotificationRule.active.is_(True))
                .all()
            )
            pairs: list[tuple[NotificationRule, NotificationChannel]] = []
            for rule in rules:
                ch = (
                    db.query(NotificationChannel)
                    .filter(
                        NotificationChannel.id == rule.channel_id,
                        NotificationChannel.active.is_(True),
                    )
                    .first()
                )
                if ch:
                    # Detach from session before storing in-memory
                    db.expunge(rule)
                    db.expunge(ch)
                    pairs.append((rule, ch))
        with self._lock:
            self._rules = pairs
        logger.info(f"NotificationDispatcher: loaded {len(pairs)} active rule(s)")

    def _refresh_loop(self) -> None:
        while True:
            time.sleep(_REFRESH_INTERVAL)
            try:
                self._load_rules()
            except Exception as exc:
                logger.warning(f"NotificationDispatcher: rule refresh failed: {exc}")

    def _dispatch(self, event: dict) -> None:
        with self._lock:
            snapshot = list(self._rules)

        for rule, channel in snapshot:
            type_match = rule.event_type == "*" or rule.event_type == event.get("event_type")
            zone_match = rule.zone_id is None or rule.zone_id == event.get("zone_id")
            if not (type_match and zone_match):
                continue
            try:
                config = (
                    json.loads(channel.config)
                    if isinstance(channel.config, str)
                    else channel.config
                )
                get_driver(channel.type).send(config, event)
                backend_notifications.labels(channel_type=channel.type).inc()
                logger.info(
                    f"NotificationDispatcher: sent {event.get('event_type')} → {channel.name}"
                )
            except Exception as exc:
                logger.warning(
                    f"NotificationDispatcher: send to '{channel.name}' failed: {exc}"
                )

    def run(self) -> None:
        self._load_rules()
        threading.Thread(
            target=self._refresh_loop, daemon=True, name="notif-refresh"
        ).start()

        r = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe("vision.events.broadcast")
        logger.info("NotificationDispatcher: listening on vision.events.broadcast")

        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = json.loads(message["data"])
                self._dispatch(event)
            except Exception as exc:
                logger.warning(f"NotificationDispatcher: dispatch error: {exc}")


def run() -> None:
    NotificationDispatcher().run()
