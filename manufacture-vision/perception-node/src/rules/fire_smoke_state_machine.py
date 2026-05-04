class FireSmokeStateMachine:
    """
    Tracks fire and smoke detections per zone.
    Requires N consecutive frames to trigger an event (hysteresis).
    Enforces a cooldown period per zone after an event fires.
    """
    def __init__(self, required_consecutive=3, cooldown_ms=300000):
        self.required_consecutive = required_consecutive
        self.cooldown_ms = cooldown_ms
        self.state = {} # zone_id: {"fire": consecutive, "smoke": consecutive}
        self.last_event_ts = {} # zone_id: ts_ms

    def update(self, zone_id: str, detected_classes: set, pts_ms: float):
        """
        detected_classes: set of classes detected in this zone in the current frame, e.g. {"fire"}
        Returns a list of events to emit, e.g. ["FIRE_DETECTED"]
        """
        if zone_id not in self.state:
            self.state[zone_id] = {"fire": 0, "smoke": 0}
            
        last_ts = self.last_event_ts.get(zone_id, 0)
        if pts_ms - last_ts < self.cooldown_ms:
            # In cooldown, reset consecutive counters just in case
            self.state[zone_id]["fire"] = 0
            self.state[zone_id]["smoke"] = 0
            return []
            
        events_fired = []
        for cls in ["fire", "smoke"]:
            if cls in detected_classes:
                self.state[zone_id][cls] += 1
                if self.state[zone_id][cls] >= self.required_consecutive:
                    events_fired.append(f"{cls.upper()}_DETECTED")
                    self.state[zone_id][cls] = 0
            else:
                self.state[zone_id][cls] = 0
                
        if events_fired:
            self.last_event_ts[zone_id] = pts_ms
            
        return events_fired
