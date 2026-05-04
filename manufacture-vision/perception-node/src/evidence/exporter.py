import os
import subprocess
import tempfile
import cv2
import numpy as np
from loguru import logger

# Overlay colours (BGR)
_COLOUR_ZONE    = (255, 100,   0)   # blue
_COLOUR_BOX_OK  = (  0, 220,   0)   # green  — zone events
_COLOUR_BOX_PPE = (  0,  40, 220)   # red    — PPE violation
_COLOUR_TEXT    = (255, 255, 255)   # white


class ClipExporter:
    """
    Writes a list of (pts_ms, frame_bgr) tuples to a temporary MP4 file.

    Optionally draws a context overlay on every frame so the clip is immediately
    interpretable by a compliance reviewer:
      • Zone polygon boundary
      • Person bounding box (green for zone events, red for PPE violations)
      • Event type + track ID label

    Called from EvidenceWorker in a background thread — never blocks the inference loop.
    Caller is responsible for deleting the temp file after upload.
    """

    def __init__(self, fps: float = 15.0):
        self.fps = fps

    def export(
        self,
        frames: list[tuple[float, np.ndarray]],
        overlay: dict | None = None,
    ) -> str | None:
        """
        Returns the path to the exported temp MP4, or None if no frames provided.

        overlay (optional) dict keys:
            bbox         – [x1, y1, x2, y2] of the tracked person
            zone_polygon – list of [x, y] coordinate pairs
            zone_id      – str label
            event_type   – str ("ZONE_ENTER", "PPE_VIOLATION", etc.)
            track_id     – int
            missing_ppe  – list[str] (for PPE_VIOLATION only)
        """
        if not frames:
            logger.warning("ClipExporter: no frames in window, skipping export")
            return None

        h, w = frames[0][1].shape[:2]

        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()

        writer = cv2.VideoWriter(
            tmp.name,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (w, h),
        )
        if not writer.isOpened():
            logger.error(f"ClipExporter: VideoWriter failed to open for {tmp.name}")
            return None

        event_ts_ms = overlay.get("event_ts_ms") if overlay else None
        for pts_ms, frame in frames:
            out = self._render(frame.copy(), overlay, pts_ms, event_ts_ms)
            writer.write(out)
        writer.release()

        # Remux with faststart so moov atom is at the start — required for browser playback
        fs_path = tmp.name.replace(".mp4", "_fs.mp4")
        proc = subprocess.run(
            ["ffmpeg", "-i", tmp.name, "-c", "copy", "-movflags", "+faststart", "-y", fs_path],
            capture_output=True,
        )
        if proc.returncode == 0:
            os.replace(fs_path, tmp.name)
        else:
            logger.warning(f"ClipExporter: ffmpeg faststart failed, using raw file: {proc.stderr.decode()[-200:]}")
            try:
                os.remove(fs_path)
            except OSError:
                pass

        logger.debug(f"ClipExporter: wrote {len(frames)} frames → {tmp.name}")
        return tmp.name

    _BBOX_WINDOW_MS = 1_000  # draw person bbox only within ±1s of event

    # ------------------------------------------------------------------
    def _render(
        self,
        frame: np.ndarray,
        overlay: dict | None,
        pts_ms: float | None = None,
        event_ts_ms: float | None = None,
    ) -> np.ndarray:
        if not overlay:
            return frame

        event_type   = overlay.get("event_type", "")
        track_id     = overlay.get("track_id", "?")
        zone_polygon = overlay.get("zone_polygon")
        bbox         = overlay.get("bbox")
        missing_ppe  = overlay.get("missing_ppe", [])

        box_colour = _COLOUR_BOX_PPE if event_type == "PPE_VIOLATION" else _COLOUR_BOX_OK

        # Person bbox — only near the event frame, not on pre/post context frames
        near_event = (
            pts_ms is None
            or event_ts_ms is None
            or abs(pts_ms - event_ts_ms) <= self._BBOX_WINDOW_MS
        )
        if bbox and near_event:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_colour, 2)
            cv2.putText(frame, f"ID:{track_id}", (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_colour, 2)

        # Event banner — only near the event frame
        if near_event:
            banner = f"! {event_type}"
            if missing_ppe:
                banner += f" | missing: {', '.join(missing_ppe)}"
            cv2.putText(frame, banner, (8, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, _COLOUR_BOX_PPE, 2)

        return frame
