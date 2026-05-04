from prometheus_client import Counter, Gauge, Histogram, start_http_server

edge_fps = Gauge("edge_fps", "Current inference FPS")
edge_queue_depth = Gauge("edge_queue_depth", "Frame buffer queue depth")
edge_active_tracks = Gauge("edge_active_tracks", "Active ByteTrack IDs")

edge_frame_drops = Counter("edge_frame_drops_total", "Frames dropped due to full buffer")
edge_events_emitted = Counter("edge_events_emitted_total", "Events published to Redis", ["event_type"])
edge_clip_uploads = Counter("edge_clip_uploads_total", "Evidence clip uploads", ["status"])

edge_inference_latency = Histogram(
    "edge_inference_latency_ms",
    "Per-frame inference latency in ms",
    buckets=[10, 20, 30, 50, 75, 100, 150, 200, 300],
)


def start_metrics_server(port: int = 9091) -> None:
    start_http_server(port)
