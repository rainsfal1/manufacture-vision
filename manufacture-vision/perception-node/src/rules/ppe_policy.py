class PPEComplianceChecker:
    """
    Enforces PPE policy per (track_id, zone_id) pair.

    Two protections against event spam:
    - Hysteresis: requires `required_consecutive` frames of continuous violation
      before firing. Resets to zero on any compliant frame.
    - Cooldown: once a violation fires, suppresses re-fires for `cooldown_ms`
      milliseconds regardless of continued non-compliance.
    """

    def __init__(self, required_consecutive: int = 3, cooldown_ms: float = 30_000):
        self.required_consecutive = required_consecutive
        self.cooldown_ms = cooldown_ms
        # (track_id, zone_id) → {"consecutive": int, "last_event_ts_ms": float}
        self._state: dict[tuple, dict] = {}

    def update(
        self,
        track_id: int,
        zone_id: str,
        missing_ppe: list[str],
        pts_ms: float,
    ) -> list[str] | None:
        """
        Call once per frame for each (track, zone) pair where the person is inside.

        Returns the list of missing PPE items when a violation should be emitted,
        otherwise returns None.
        """
        key = (track_id, zone_id)

        if not missing_ppe:
            # Compliant this frame — reset hysteresis counter
            if key in self._state:
                self._state[key]["consecutive"] = 0
            return None

        if key not in self._state:
            # last_event_ts_ms = -inf so the first violation always fires immediately
            self._state[key] = {"consecutive": 0, "last_event_ts_ms": float("-inf")}

        state = self._state[key]
        state["consecutive"] += 1

        if state["consecutive"] >= self.required_consecutive:
            elapsed = pts_ms - state["last_event_ts_ms"]
            if elapsed >= self.cooldown_ms:
                state["last_event_ts_ms"] = pts_ms
                state["consecutive"] = 0
                return list(missing_ppe)

        return None
