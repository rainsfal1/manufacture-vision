import os
import queue
import time
from loguru import logger


class EvidenceWorker:
    """
    Background daemon thread that handles clip export, MinIO upload, and Redis publish.

    The main inference loop calls submit() (non-blocking). This worker picks up jobs,
    waits for post-event frames to accumulate, exports the clip, uploads to MinIO,
    attaches clip_ref to the event payload, then publishes to Redis.

    This design ensures the inference loop never stalls on disk I/O or network uploads.

    Deduplication: only one clip is produced per (zone_id, event_type) within a rolling
    window (dedup_window_ms, defaults to the PPE cooldown). Subsequent events in the same
    zone/window reuse the first clip's clip_ref. The reused clip covers the first
    offender's timeframe — the backend (Phase 4) is responsible for full incident grouping.
    """

    def __init__(
        self,
        ring_buffer,
        exporter,
        uploader,
        publisher,
        pre_s: float = 5.0,
        post_s: float = 5.0,
        queue_size: int = 10,
        dedup_window_ms: float = 30_000,
    ):
        self._ring_buffer = ring_buffer
        self._exporter = exporter
        self._uploader = uploader
        self._publisher = publisher
        self._pre_s = pre_s
        self._post_s = post_s
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self.upload_success: int = 0
        self.upload_failure: int = 0

        self._dedup_window_ms = dedup_window_ms
        # { (zone_id, event_type): (last_clip_ts_ms, clip_ref_str) }
        self._dedup_state: dict[tuple, tuple] = {}

    def submit(self, event_type: str, payload: dict) -> None:
        """
        Non-blocking. Called from the main inference loop.
        Drops the job (with a warning) if the worker queue is full.
        """
        try:
            self._queue.put_nowait((event_type, dict(payload)))
        except queue.Full:
            logger.warning(
                f"EvidenceWorker: queue full, dropping evidence for {event_type}"
            )

    def run(self) -> None:
        """Blocking loop — run as a daemon thread target."""
        while True:
            event_type, payload = self._queue.get()
            try:
                self._process(event_type, payload)
            except Exception as e:
                logger.error(f"EvidenceWorker: unhandled error processing {event_type}: {e}")
            finally:
                self._queue.task_done()

    def _process(self, event_type: str, payload: dict) -> None:
        ts_ms = payload["event_ts_ms"]
        zone_id = payload.get("zone_id", "unknown")
        dedup_key = (zone_id, event_type)

        # --- Deduplication check ---
        existing = self._dedup_state.get(dedup_key)
        if existing:
            last_ts_ms, last_clip_ref = existing
            if (ts_ms - last_ts_ms) < self._dedup_window_ms:
                logger.info(
                    f"EvidenceWorker: dedup hit for {event_type} in {zone_id} "
                    f"(Δ{(ts_ms - last_ts_ms)/1000:.1f}s < window {self._dedup_window_ms/1000:.0f}s) "
                    f"— reusing clip_ref"
                )
                payload["clip_ref"] = last_clip_ref
                self._publisher.publish(event_type, payload)
                return

        # --- New incident: wait for post-event frames, then export ---
        post_s = payload.get("clip_post_s", self._post_s)
        time.sleep(post_s)

        pre_s = payload.get("clip_pre_s", self._pre_s)
        frames = self._ring_buffer.get_window(ts_ms, pre_s, post_s)

        overlay = {
            "event_type":   event_type,
            "event_ts_ms":  ts_ms,
            "track_id":     payload.get("track_id"),
            "bbox":         payload.get("bbox"),
            "zone_polygon": payload.get("zone_polygon"),
            "missing_ppe":  payload.get("missing_ppe", []),
        }

        clip_path = self._exporter.export(frames, overlay=overlay)

        clip_ref = None
        if clip_path:
            track_id = payload.get("track_id", "x")
            object_key = f"clips/{int(ts_ms)}_{track_id}_{event_type}.mp4"
            clip_ref = self._uploader.upload(clip_path, object_key)
            try:
                os.remove(clip_path)
            except OSError:
                pass

        if clip_ref:
            clip_ref_str = str(clip_ref)
            payload["clip_ref"] = clip_ref_str
            self.upload_success += 1
            # Record for dedup — only on successful upload
            self._dedup_state[dedup_key] = (ts_ms, clip_ref_str)
        else:
            payload["clip_ref"] = "null"
            self.upload_failure += 1

        self._publisher.publish(event_type, payload)
