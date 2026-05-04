import av
import cv2
import time
import redis as redis_lib

from config.settings import settings
from loguru import logger


def _wait_for_demo_signal(label: str = "start") -> None:
    """Block until a 'demo.replay' pub/sub message is received for this source or 'all'."""
    logger.info(f"[{settings.SOURCE_ID}] Waiting for demo signal to {label}...")
    r = redis_lib.from_url(settings.REDIS_URL)
    p = r.pubsub()
    p.subscribe("demo.replay")
    while True:
        msg = p.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg:
            data = msg["data"].decode("utf-8")
            if data in (settings.SOURCE_ID, "all"):
                logger.info(f"[{settings.SOURCE_ID}] Demo signal received ({data}). {label.capitalize()}ing!")
                p.unsubscribe()
                return


class PyAVVideoReader:
    """
    Reads an MP4 stream using PyAV for monotonic PTS extraction.
    Ensures PTS-aligned pacing.

    When loop=True the reader does NOT start automatically — it waits for
    a 'demo.replay' Redis pub/sub signal before the first play and before
    each subsequent replay.
    """
    def __init__(self, source_path: str, loop: bool = False):
        self.source_path = source_path
        self.loop = loop
        self.container = None
        self.video_stream = None
        self._start_playback_time = None
        self._first_pts = None

    def start(self):
        logger.info(f"Opening video source via PyAV: {self.source_path}")
        self.container = av.open(self.source_path)
        self.video_stream = self.container.streams.video[0]
        self._start_playback_time = None
        self._first_pts = None

    def read_frames(self):
        """
        Generator producing (frame_bgr, pts_ms) and pacing the output.

        If loop=True:
          - Waits for demo.replay signal before the FIRST play.
          - After video ends, waits again before replaying.
        """
        # ── Wait for the initial Demo button press ──────────────────────────
        if self.loop:
            _wait_for_demo_signal("start")

        if not self.container:
            self.start()

        while True:
            try:
                for frame in self.container.decode(self.video_stream):
                    original_pts = frame.pts
                    time_base = self.video_stream.time_base
                    if original_pts is None:
                        logger.debug("Frame had no PTS, skipping.")
                        continue

                    pts_ms = float(original_pts * time_base * 1000)

                    if self._first_pts is None:
                        self._first_pts = pts_ms
                        self._start_playback_time = time.time()

                    # PTS-aligned pacing
                    expected_time_elapsed = (pts_ms - self._first_pts) / 1000.0
                    actual_time_elapsed = time.time() - self._start_playback_time
                    sleep_time = expected_time_elapsed - actual_time_elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    img_rgb = frame.to_ndarray(format="rgb24")
                    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

                    wall_pts_ms = (self._start_playback_time * 1000.0) + (pts_ms - self._first_pts)
                    yield img_bgr, wall_pts_ms

                # ── End of stream ───────────────────────────────────────────
                if self.loop:
                    # Wait for the next Demo press before replaying
                    _wait_for_demo_signal("replay")
                    self.container.seek(0)
                    self._start_playback_time = time.time()
                    self._first_pts = None
                else:
                    logger.info("End of stream reached, terminating.")
                    break

            except Exception as e:
                logger.error(f"PyAV Error: {e}")
                break

    def close(self):
        if self.container:
            self.container.close()
            self.container = None
            logger.info("Closed PyAV stream.")
