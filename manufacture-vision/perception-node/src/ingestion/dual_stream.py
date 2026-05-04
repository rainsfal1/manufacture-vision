import cv2
from loguru import logger

from config.settings import settings
from ingestion.reader import PyAVVideoReader
from ingestion.frame_buffer import FrameBuffer
from evidence.ring_buffer import RingBuffer


class DualStreamReader:
    """
    Wraps PyAVVideoReader and fans each frame out to two destinations:

    1. RingBuffer (high-res, native resolution) — for evidence clip export
    2. FrameBuffer (low-res, resized) — for AI inference (drop-oldest policy)

    Frame skipping: only every Nth frame (FRAME_SKIP) is sent to inference.
    The ring buffer still receives ALL frames for evidence clip quality.

    Designed to run as the ingest thread target, replacing the old ingest_loop.
    Sends a (None, None) sentinel to the inference buffer when the stream ends.
    """

    def __init__(
        self,
        reader: PyAVVideoReader,
        inference_buffer: FrameBuffer,
        ring_buffer: RingBuffer,
        low_res_width: int = 416,
        uploader = None,
        source_id: str = "unknown"
    ):
        self._reader = reader
        self._inference_buffer = inference_buffer
        self._ring_buffer = ring_buffer
        self._low_res_width = low_res_width
        self._uploader = uploader
        self._source_id = source_id
        self._frame_skip = max(1, settings.FRAME_SKIP)
        # Set on first frame — used by main loop to scale bbox to native coords
        self.native_wh: tuple[int, int] | None = None

    def run(self) -> None:
        logger.info(f"DualStreamReader: started (low-res width={self._low_res_width}px, frame_skip={self._frame_skip})")
        first_frame = True
        frame_count = 0
        for frame_bgr, pts_ms in self._reader.read_frames():
            frame_count += 1

            # High-res → ring buffer (always, every frame, no drop)
            if self.native_wh is None:
                h, w = frame_bgr.shape[:2]
                self.native_wh = (w, h)
                logger.debug(f"DualStreamReader: native resolution {w}×{h}, low-res {self._low_res_width}×{int(h * self._low_res_width / w)}")
            self._ring_buffer.put(pts_ms, frame_bgr)
            
            if first_frame and self._uploader:
                try:
                    success, buffer = cv2.imencode(".jpg", frame_bgr)
                    if success:
                        obj_name = f"snapshots/{self._source_id}.jpg"
                        self._uploader.upload_bytes(obj_name, buffer.tobytes(), "image/jpeg")
                        logger.info(f"Uploaded initial snapshot for zone editor to {obj_name}")
                except Exception as e:
                    logger.error(f"Failed to upload initial snapshot: {e}")
                first_frame = False

            # Skip frames for inference — only process every Nth frame
            if frame_count % self._frame_skip != 0:
                continue

            # Low-res → inference queue (drop-oldest when full)
            h, w = frame_bgr.shape[:2]
            scale = self._low_res_width / w
            low_res = cv2.resize(frame_bgr, (self._low_res_width, int(h * scale)))
            self._inference_buffer.put((low_res, pts_ms))

        # Signal end of stream to inference loop
        self._inference_buffer.put((None, None))
        logger.info("DualStreamReader: stream ended, sentinel sent")
