"""
Channel drivers for Phase 9 notification dispatch.

Each driver exposes a single send(config, payload) method.
Raises on failure (caller catches and logs as WARNING).
"""
import json

import httpx
from loguru import logger

_TIMEOUT = 5.0


class SlackDriver:
    """Sends a Slack Block Kit message to an incoming webhook URL."""

    def send(self, config: dict, payload: dict) -> None:
        missing = payload.get("missing_ppe") or []
        if isinstance(missing, str):
            try:
                missing = json.loads(missing)
            except Exception:
                missing = [missing]

        text = (
            f"*⚠ {payload.get('event_type', 'EVENT')}* — `{payload.get('zone_id', '?')}`\n"
            f"Missing: {', '.join(missing) if missing else '—'} · "
            f"Track {payload.get('track_id', '?')} · {payload.get('source_id', '?')}"
        )
        blocks: list = [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]

        clip = payload.get("clip_key") or payload.get("clip_ref")
        if clip:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Clip: `{clip}`"}],
            })

        resp = httpx.post(config["url"], json={"blocks": blocks}, timeout=_TIMEOUT)
        resp.raise_for_status()


class WebhookDriver:
    """Posts the raw event payload as JSON to an arbitrary URL."""

    def send(self, config: dict, payload: dict) -> None:
        headers = config.get("headers") or {}
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except Exception:
                headers = {}
        resp = httpx.post(config["url"], json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()


class EmailDriver:
    """Stub — SMTP implementation deferred. Logs but never raises."""

    def send(self, config: dict, payload: dict) -> None:
        logger.info(
            f"[EmailDriver] would send to {config.get('to', '?')}: "
            f"{payload.get('event_type')} in {payload.get('zone_id')}"
        )


_DRIVERS: dict[str, SlackDriver | WebhookDriver | EmailDriver] = {
    "slack": SlackDriver(),
    "webhook": WebhookDriver(),
    "email": EmailDriver(),
}


def get_driver(channel_type: str) -> SlackDriver | WebhookDriver | EmailDriver:
    driver = _DRIVERS.get(channel_type)
    if driver is None:
        raise ValueError(f"Unknown channel type: {channel_type!r}")
    return driver
