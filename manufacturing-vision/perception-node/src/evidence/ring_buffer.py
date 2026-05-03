from collections import deque
import threading
import numpy as np


class RingBuffer:
    """
    Thread-safe rolling frame cache keyed by PTS timestamp (ms).

    Written by the ingest thread, read by the EvidenceWorker thread.
    Evicts frames older than `retention_ms` on every write to keep memory bounded.
    """

    def __init__(self, retention_ms: float = 30_000):
        self._retention_ms = retention_ms
        self._frames: deque[tuple[float, np.ndarray]] = deque()
        self._lock = threading.Lock()

    def put(self, pts_ms: float, frame: np.ndarray) -> None:
        with self._lock:
            self._frames.append((pts_ms, frame))
            cutoff = pts_ms - self._retention_ms
            while self._frames and self._frames[0][0] < cutoff:
                self._frames.popleft()

    def get_window(self, ts_ms: float, before_s: float, after_s: float) -> list[tuple[float, np.ndarray]]:
        """
        Returns copies of all frames within [ts_ms - before_s*1000, ts_ms + after_s*1000].
        Copies prevent frames from being mutated while the exporter is writing them.
        """
        with self._lock:
            start = ts_ms - before_s * 1000
            end   = ts_ms + after_s  * 1000
            return [(pts, f.copy()) for pts, f in self._frames if start <= pts <= end]

    def size(self) -> int:
        with self._lock:
            return len(self._frames)
