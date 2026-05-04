import queue
from loguru import logger

class FrameBuffer:
    """
    A temporal frame buffer that enforces bounded latency and drop policies.
    Queue depth is fixed (e.g. 5 frames) to avoid unbounded backlog.
    When full, the oldest frame is dropped to preserve temporal freshness.
    """
    def __init__(self, maxsize: int = 5):
        self.queue = queue.Queue(maxsize=maxsize)
        self.drops = 0

    def put(self, frame_item: tuple):
        """
        Attempts to put an item (frame, pts_ms) onto the queue.
        If the queue is full, the oldest frame is dropped immediately to maintain freshness.
        """
        while True:
            try:
                self.queue.put_nowait(frame_item)
                break
            except queue.Full:
                try:
                    # Drop the oldest frame to make space
                    dropped_item = self.queue.get_nowait()
                    self.drops += 1
                    logger.warning(
                        f"FrameBuffer overload: queue full, dropping oldest frame (PTS={dropped_item[1]} ms). Total drops: {self.drops}"
                    )
                except queue.Empty:
                    # Rare race condition if another consumer pulled it
                    pass

    def get(self, timeout=None):
        """
        Retrieves the next frame item from the queue.
        """
        return self.queue.get(timeout=timeout)

    def size(self) -> int:
        return self.queue.qsize()

    def get_drops(self) -> int:
        return self.drops
