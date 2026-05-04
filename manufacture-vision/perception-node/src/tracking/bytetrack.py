import supervision as sv
import numpy as np

class TrackedObject:
    def __init__(self, track_id: int, bbox: list, pts_ms: float):
        self.track_id = track_id
        self.bbox = bbox
        self.first_seen_pts = pts_ms
        self.last_seen_pts = pts_ms
        self.age = 1

    def update(self, bbox: list, pts_ms: float):
        self.bbox = bbox
        self.last_seen_pts = pts_ms
        self.age += 1

class ByteTrackTracker:
    """
    ByteTrack implementation utilizing Supervision.
    Maintains an extended track state containing first_seen_pts to enable temporal analytics.
    """
    def __init__(self):
        self.tracker = sv.ByteTrack()
        self.active_tracks = {}

    def update(self, detections: list, pts_ms: float) -> list:
        """
        Takes raw [bbox, conf, class_id] arrays from detector and updates tracked objects.
        Returns the active Tracks for the current frame.
        """
        if not detections:
            # We still step the tracker to gracefully age lost tracks out
            # Supervision doesn't expose a clean step without detections natively,
            # so we'll just handle cleanups manually or with empty Detections
            empty_sv_detections = sv.Detections.empty()
            self.tracker.update_with_detections(empty_sv_detections)
            return []

        # Convert our raw list to supervision Detections object
        xyxy = np.array([d[0] for d in detections], dtype=np.float32)
        confidence = np.array([d[1] for d in detections], dtype=np.float32)
        class_id = np.array([d[2] for d in detections], dtype=np.int32)
        
        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id
        )

        tracked_detections = self.tracker.update_with_detections(sv_detections)
        
        current_frame_tracks = []
        current_frame_ids = set()

        # Update our extended TrackedObject states
        for i in range(len(tracked_detections)):
            box = tracked_detections.xyxy[i].tolist()
            tracker_id = int(tracked_detections.tracker_id[i])
            current_frame_ids.add(tracker_id)

            if tracker_id in self.active_tracks:
                self.active_tracks[tracker_id].update(box, pts_ms)
            else:
                self.active_tracks[tracker_id] = TrackedObject(tracker_id, box, pts_ms)
            
            current_frame_tracks.append(self.active_tracks[tracker_id])

        # Purge dead tracks to prevent memory leaks over long runs
        dead_ids = set(self.active_tracks.keys()) - current_frame_ids
        for tid in dead_ids:
            # Note: A real tracker might keep them around for a few frames in a 'lost' state
            # before purging. ByteTrack handles re-ID internally over short windows.
            # We purge them here if ByteTrack drops them to keep tracking dictionary clean.
            # We could use `self.tracker.lost_tracks` if tighter control is needed.
            # For Step 1, immediate purge on drop is OK if ByteTrack already aged them.
            del self.active_tracks[tid]

        return current_frame_tracks
