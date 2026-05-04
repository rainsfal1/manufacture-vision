import os
import sys

# --- SURGICAL SILENCE BLOCK ---
# macOS ObjC Runtime warnings about duplicate libraries (cv2 vs av) 
# are emitted to stderr from C-level code. We silence them using os.dup2.
def silent_imports():
    _stderr_fd = sys.stderr.fileno()
    stderr_copy = os.dup(_stderr_fd)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, _stderr_fd)
    try:
        import av
        import cv2
        return av, cv2
    finally:
        os.dup2(stderr_copy, _stderr_fd)
        os.close(devnull)
        os.close(stderr_copy)

av, cv2 = silent_imports()
# -----------------------------

import threading
import time
import json
from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

from config.settings import settings
from ingestion.reader import PyAVVideoReader
from ingestion.frame_buffer import FrameBuffer
from detection.onnx_runner import PersonDetector
from detection.ppe_detector import PPEDetector
from detection.fire_smoke_detector import FireSmokeDetector
from tracking.bytetrack import ByteTrackTracker
from spatial.geometry import PolygonZone
from rules.state_machine import ZoneStateMachine
from rules.ppe_policy import PPEComplianceChecker
from rules.fire_smoke_state_machine import FireSmokeStateMachine
from outputs.spine_pub import SpinePublisher
from telemetry.monitor import TelemetryMonitor
from telemetry import health
from ingestion.dual_stream import DualStreamReader
from evidence.ring_buffer import RingBuffer
from evidence.exporter import ClipExporter
from evidence.s3_uploader import MinIOUploader
from evidence.worker import EvidenceWorker

# Suppress macOS duplicate library warnings for cleaner audit logs
os.environ["PYAV_FFMPEG_DIR"] = "/tmp/none"
os.environ["OPENCV_VIDEOIO_PRIORITY_BACKEND"] = "AVFOUNDATION"

# Set up Rich Console for premium output
console = Console()

# Configure Loguru to use RichHandler or JSON based on LOG_FORMAT
logger.remove()
if settings.LOG_FORMAT == "json":
    logger.add(sys.stdout, serialize=True, level="INFO")
else:
    logger.add(
        RichHandler(console=console, rich_tracebacks=True, markup=True, show_path=False),
        format="{message}",
        level="INFO",
    )

def show_welcome():
    welcome_text = Text.assemble(
        ("PERCEPTION NODE ", "bold cyan"),
        ("v1.0 (Step 1) ", "bold magenta"),
        ("\n", ""),
        ("Core Perception Engine is Online", "italic white")
    )
    console.print(Panel(welcome_text, border_style="cyan", padding=(1, 2)))

def ingest_loop(reader: PyAVVideoReader, buffer: FrameBuffer):
    """
    Runs in a dedicated thread.
    Reads frames at a paced PTS rate and drops oldest when buffer is full.
    """
    logger.info("Ingest loop started.")
    for frame_data in reader.read_frames():
        buffer.put(frame_data)
        
    # Send sentinel to terminate
    buffer.put((None, None))
    logger.info("Ingest loop finished.")

def load_zones(path: str) -> list:
    """Load zone config — tries backend API first, falls back to zones.json."""
    if settings.BACKEND_URL:
        try:
            import httpx
            resp = httpx.get(f"{settings.BACKEND_URL}/zones", timeout=5.0)
            resp.raise_for_status()
            zones = []
            for z in resp.json():
                poly = z.get("polygon") or []
                ppe = z.get("required_ppe") or []
                if poly:
                    zones.append(PolygonZone(z["zone_id"], poly, required_ppe=ppe))
            logger.info(f"Loaded {len(zones)} zones from backend API ({settings.BACKEND_URL})")
            return zones
        except Exception as e:
            logger.warning(f"Could not load zones from backend ({e}) — falling back to {path}")

    # File fallback
    zones = []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        for z_name, zone_data in data.get("zones", {}).items():
            if isinstance(zone_data, list):
                coords = zone_data
                required_ppe = []
            else:
                coords = zone_data.get("polygon", [])
                required_ppe = zone_data.get("required_ppe", [])
            zones.append(PolygonZone(z_name, coords, required_ppe=required_ppe))
        logger.info(f"Loaded {len(zones)} zones from {path}")
    except FileNotFoundError:
        logger.warning(f"Zone config not found at {path}. No zones active.")
    return zones

def render_debug_overlay(frame, tracks, zones, output_video, event_messages):
    """Draws overlays for Deliverable I verification."""
    # Draw standard bounding boxes and IDs
    for t in tracks:
        x1, y1, x2, y2 = [int(v) for v in t.bbox]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID: {t.track_id} | Age: {t.age}", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw footpoints
        center_x = x1 + (x2 - x1) / 2
        bottom_y = y2
        cv2.circle(frame, (int(center_x), int(bottom_y)), 5, (0, 0, 255), -1)


    # Draw Event messages for 30 frames (simplified)
    # in an actual app you'd fade these or queue them.
    y_offset = 30
    for msg in event_messages:
        cv2.putText(frame, msg, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        y_offset += 30
        
    if output_video:
        output_video.write(frame)

def main():
    show_welcome()
    logger.info("Initializing components...")
    
    # 1. Initialize Components
    reader = PyAVVideoReader(settings.INPUT_STREAM, loop=True)
    buffer = FrameBuffer(maxsize=5) # Real-Time backpressure
    
    # We assume 'yolov8n.onnx' is downloaded via tools script
    detector = PersonDetector("models/yolov8n.onnx", conf_thresh=0.4)
    detector.initialize()

    ppe_detector = PPEDetector(settings.PPE_MODEL_PATH, conf_thresh=settings.PPE_CONF_THRESH)
    ppe_detector.initialize()

    compliance_checker = PPEComplianceChecker(
        required_consecutive=settings.PPE_VIOLATION_HYSTERESIS,
        cooldown_ms=settings.PPE_VIOLATION_COOLDOWN_MS,
    )

    tracker = ByteTrackTracker()

    fs_detector = FireSmokeDetector(settings.FIRE_SMOKE_MODEL_PATH, conf_thresh=settings.FIRE_SMOKE_CONF_THRESH)
    fs_detector.initialize()

    fs_state_machine = FireSmokeStateMachine(
        required_consecutive=settings.FIRE_SMOKE_HYSTERESIS,
        cooldown_ms=settings.FIRE_SMOKE_COOLDOWN_MS
    )

    zones = load_zones(settings.ZONES_CONFIG_PATH)
    state_machine = ZoneStateMachine(required_consecutive=2)
    _ppe_frame_counter: dict[tuple, int] = {}
    _ppe_last_missing: dict[tuple, list] = {}
    _ppe_wall_ts: dict[tuple, float] = {}
    PPE_INFER_EVERY = 3

    publisher = SpinePublisher()
    monitor = TelemetryMonitor()

    # Evidence pipeline (Phase 3)
    ring_buffer = RingBuffer(retention_ms=settings.RING_BUFFER_RETENTION_S * 1000)
    exporter    = ClipExporter(fps=settings.FPS_LIMIT)
    uploader    = MinIOUploader(
        settings.MINIO_ENDPOINT,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
        settings.MINIO_BUCKET,
        secure=settings.MINIO_SECURE,
    )
    evidence_worker = EvidenceWorker(
        ring_buffer, exporter, uploader, publisher,
        pre_s=settings.CLIP_PRE_EVENT_S,
        post_s=settings.CLIP_POST_EVENT_S,
        dedup_window_ms=settings.PPE_VIOLATION_COOLDOWN_MS,
    )
    dual_stream = DualStreamReader(
        reader, buffer, ring_buffer,
        low_res_width=settings.LOW_RES_WIDTH,
        uploader=uploader,
        source_id=settings.SOURCE_ID
    )

    # 2. Setup Debug Video Output
    out_video = None
    if settings.DEBUG_OVERLAY:
        pass

    # Start Prometheus metrics server
    health.start_metrics_server(settings.METRICS_PORT)
    logger.info(f"Prometheus metrics server started on port {settings.METRICS_PORT}")

    # 3. Start Ingest + Evidence threads
    threading.Thread(target=dual_stream.run, daemon=True, name="ingest").start()
    threading.Thread(target=evidence_worker.run, daemon=True, name="evidence").start()
    
    # 4. Main Inference Loop
    logger.info("Entering main inference loop.")
    event_messages = [] # For overlay fading
    
    try:
        while True:
            # Drop older frames if backlogged
            # But the blocking get() ensures we wait if queue is empty
            item = buffer.get()
            
            frame, pts_ms = item
            if frame is None: # Sentinel
                break
                
            # --- Inference Pipeline ---
            detections = detector.detect(frame)
            active_tracks = tracker.update(detections, pts_ms)
            fs_detections = fs_detector.detect(frame)
            
            # --- Spatial Logic & Event Engine ---
            for track in active_tracks:
                for zone in zones:
                    # Is footpoint in polygon?
                    is_inside = zone.check_zone(track.bbox)
                    
                    # Update state machine (handles Hysteresis)
                    transition = state_machine.update(track.track_id, zone.zone_id, is_inside) if settings.ENABLE_ZONE_INTRUSION else None
                    
                    if transition: # ZONE_ENTER or ZONE_EXIT
                        logger.info(f"Transition [{transition}] emitted for Track {track.track_id} in {zone.zone_id}")
                        event_messages.insert(0, f"{transition} -> Track {track.track_id} in {zone.zone_id}")

                        # Maintain list small
                        if len(event_messages) > 3:
                            event_messages.pop()

                        _s = (dual_stream.native_wh[0] / settings.LOW_RES_WIDTH
                              if dual_stream.native_wh else 1.0)

                        if transition == "ZONE_ENTER":
                            # Route through evidence worker so a clip is captured
                            evidence_worker.submit(transition, {
                                "event_ts_ms": pts_ms,
                                "track_id": track.track_id,
                                "zone_id": zone.zone_id,
                                "bbox": [v * _s for v in track.bbox],
                                "confidence": 100.0,
                                "zone_polygon": zone.polygon.reshape(-1, 2).tolist(),
                            })
                        else:
                            # ZONE_EXIT: publish directly, no clip needed
                            publisher.publish(transition, {
                                "event_ts_ms": pts_ms,
                                "track_id": track.track_id,
                                "zone_id": zone.zone_id,
                                "bbox": [v * _s for v in track.bbox],
                                "confidence": 100.0,
                            })

                        health.edge_events_emitted.labels(event_type=transition).inc()

                        # Record for Telemetry
                        monitor.record_event(pts_ms)

                    # --- PPE Compliance Check (Phase 2) ---
                    if settings.ENABLE_PPE_COMPLIANCE and is_inside and zone.required_ppe:
                        _ppe_key = (track.track_id, zone.zone_id)
                        _ppe_frame_counter[_ppe_key] = (_ppe_frame_counter.get(_ppe_key, 0) + 1)

                        # Use wall-clock for cooldown so pts_ms resets on video loop don't break it
                        _now_s = time.monotonic()
                        _in_cooldown = (
                            (_now_s - _ppe_wall_ts.get(_ppe_key, 0.0)) * 1000
                            < compliance_checker.cooldown_ms
                        )

                        if _in_cooldown:
                            continue  # skip this zone entirely — violation already fired recently

                        # Run ONNX inference on first appearance and then every Nth frame
                        if _ppe_key not in _ppe_last_missing or _ppe_frame_counter[_ppe_key] % PPE_INFER_EVERY == 0:
                            _native = ring_buffer.get_frame_at(pts_ms)
                            if _native is not None:
                                _ppe_s = dual_stream.native_wh[0] / settings.LOW_RES_WIDTH if dual_stream.native_wh else 1.0
                                _native_bbox = [v * _ppe_s for v in track.bbox]
                                crop = ppe_detector.crop_person(_native, _native_bbox)
                            else:
                                crop = ppe_detector.crop_person(frame, track.bbox)
                            wearing = ppe_detector.detect_ppe(crop, zone.required_ppe)
                            _ppe_last_missing[_ppe_key] = [
                                item for item in zone.required_ppe if not wearing.get(item, False)
                            ]

                        missing = _ppe_last_missing[_ppe_key]
                        violation = compliance_checker.update(track.track_id, zone.zone_id, missing, pts_ms)
                        if violation:
                            msg = f"PPE_VIOLATION -> Track {track.track_id} missing {violation} in {zone.zone_id}"
                            logger.warning(msg)
                            event_messages.insert(0, msg)
                            if len(event_messages) > 3:
                                event_messages.pop()

                            # Scale bbox from low-res inference space → native clip space
                            _s = (dual_stream.native_wh[0] / settings.LOW_RES_WIDTH
                                  if dual_stream.native_wh else 1.0)
                            evidence_worker.submit("PPE_VIOLATION", {
                                "event_ts_ms": pts_ms,
                                "track_id": track.track_id,
                                "zone_id": zone.zone_id,
                                "bbox": [v * _s for v in track.bbox],
                                "confidence": 100.0,
                                "missing_ppe": violation,
                                "required_ppe": zone.required_ppe,
                                "zone_polygon": zone.polygon.reshape(-1, 2).tolist(),
                            })
                            health.edge_events_emitted.labels(event_type="PPE_VIOLATION").inc()
                            monitor.record_event(pts_ms)
                            _ppe_wall_ts[_ppe_key] = time.monotonic()

            # --- Fire/Smoke Logic ---
            if settings.ENABLE_FIRE_SMOKE:
                # Fire/smoke is a frame-level hazard — not restricted to PPE zones
                fs_classes = set()
                fs_best_conf = {}
                fs_best_bbox = {}

                for d in fs_detections:
                    cls_name = d["class_name"]
                    fs_classes.add(cls_name)
                    if d["confidence"] > fs_best_conf.get(cls_name, 0.0):
                        fs_best_conf[cls_name] = d["confidence"]
                        fs_best_bbox[cls_name] = d["bbox"]

                fs_events = fs_state_machine.update("frame", fs_classes, pts_ms)
                for ev in fs_events:
                    cls_name = "fire" if "FIRE" in ev else "smoke"
                    msg = f"{ev} at {fs_best_conf[cls_name]:.1f}% confidence"
                    logger.warning(msg)
                    event_messages.insert(0, msg)
                    if len(event_messages) > 3:
                        event_messages.pop()

                    _s = (dual_stream.native_wh[0] / settings.LOW_RES_WIDTH
                          if dual_stream.native_wh else 1.0)
                    evidence_worker.submit(ev, {
                        "event_ts_ms": pts_ms,
                        "track_id": 0,
                        "zone_id": "frame",
                        "bbox": [v * _s for v in fs_best_bbox[cls_name]],
                        "confidence": fs_best_conf[cls_name],
                        "detection_class": cls_name,
                        "frame_confidence": fs_best_conf[cls_name],
                        "clip_pre_s": settings.FIRE_SMOKE_PRE_EVENT_S,
                    })
                    health.edge_events_emitted.labels(event_type=ev).inc()
                    monitor.record_event(pts_ms)

            # --- Telemetry & Debug ---
            # Simulate overload if env flag set (for acceptance testing)
            import os
            if os.getenv("SIMULATE_OVERLOAD"):
                time.sleep(0.3) # 300ms explicit delay to force dropping

            monitor.update(
                pts_ms, buffer.size(), buffer.get_drops(), len(active_tracks),
                clip_ok=evidence_worker.upload_success,
                clip_fail=evidence_worker.upload_failure,
            )
            
            if settings.DEBUG_OVERLAY:
                if out_video is None:
                    h, w = frame.shape[:2]
                    out_video = cv2.VideoWriter(settings.DEBUG_OUTPUT_PATH, cv2.VideoWriter_fourcc(*'mp4v'), settings.FPS_LIMIT, (w, h))
                render_debug_overlay(frame.copy(), active_tracks, zones, out_video, event_messages)
                
    except KeyboardInterrupt:
        logger.info("Graceful shutdown requested.")
    finally:
        logger.info("Cleaning up resources.")
        reader.close()
        if out_video:
            out_video.release()
            
    logger.info("Perception Node closed successfully.")

if __name__ == "__main__":
    main()
