import time
from loguru import logger
from telemetry import health

class TelemetryMonitor:
    """
    Accumulates and logging diagnostics for observability (Deliverable I).
    """
    def __init__(self):
        self.start_time = time.time()
        self.frames_processed = 0
        self.total_pipeline_latency_ms = 0.0

        self.last_event_timestamp = None
        self.last_log_time = self.start_time
        self.log_interval_sec = 5.0 # Log every 5 seconds

        self._prev_drops = 0
        self._prev_clip_ok = 0
        self._prev_clip_fail = 0

    def record_event(self, pts_ms: float):
        """Records the timestamp of the last emitted event."""
        self.last_event_timestamp = pts_ms

    def update(self, pts_ms: float, queue_depth: int, drops: int, active_tracks: int,
               clip_ok: int = 0, clip_fail: int = 0):
        self.frames_processed += 1
        
        # Pipeline Processing Latency = Time Now - PTS of Frame Currently Finished
        # Need to re-anchor PTS since time() is epoch but PTS is relative
        # This will be exact if PTS timing logic aligns starting from 0
        now_ms = time.time() * 1000.0
        self.total_pipeline_latency_ms += now_ms - pts_ms
        
        # Prometheus: per-frame latency observation
        health.edge_inference_latency.observe(now_ms - pts_ms)
        health.edge_queue_depth.set(queue_depth)
        health.edge_active_tracks.set(active_tracks)

        # Prometheus: delta counters (cumulative values from EvidenceWorker)
        drop_delta = max(0, drops - self._prev_drops)
        ok_delta = max(0, clip_ok - self._prev_clip_ok)
        fail_delta = max(0, clip_fail - self._prev_clip_fail)
        if drop_delta:
            health.edge_frame_drops.inc(drop_delta)
        if ok_delta:
            health.edge_clip_uploads.labels(status="ok").inc(ok_delta)
        if fail_delta:
            health.edge_clip_uploads.labels(status="fail").inc(fail_delta)
        self._prev_drops = drops
        self._prev_clip_ok = clip_ok
        self._prev_clip_fail = clip_fail

        current_time = time.time()
        if (current_time - self.last_log_time) >= self.log_interval_sec:
            avg_process_fps = self.frames_processed / self.log_interval_sec
            avg_latency = self.total_pipeline_latency_ms / self.frames_processed if self.frames_processed > 0 else 0.0
            last_event_str = f"{self.last_event_timestamp:.1f}" if self.last_event_timestamp else "None"

            health.edge_fps.set(avg_process_fps)

            logger.info(
                f"[bold magenta]STATS[/bold magenta] | "
                f"FPS: [yellow]{avg_process_fps:.1f}[/yellow] | "
                f"Queue: [blue]{queue_depth}/5[/blue] | "
                f"Drops: [red]{drops}[/red] | "
                f"Latency: [green]{avg_latency:.1f}ms[/green] | "
                f"Tracks: [cyan]{active_tracks}[/cyan] | "
                f"Event: [white]{last_event_str}[/white] | "
                f"Clips: [green]✓{clip_ok}[/green]/[red]✗{clip_fail}[/red]"
            )

            self.frames_processed = 0
            self.total_pipeline_latency_ms = 0.0
            self.last_log_time = current_time
