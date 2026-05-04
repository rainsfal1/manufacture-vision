import logging

logger = logging.getLogger(__name__)

class ZoneStateMachine:
    """
    Tracks state transitions of objects relative to zones with hysteresis.
    Prevents boundary flicker rapidly switching between ENTER and EXIT.
    """
    def __init__(self, required_consecutive: int = 2):
        self.required_consecutive = required_consecutive
        
        # Maps (track_id, zone_id) -> state information
        # State object: {"status": "INSIDE"|"OUTSIDE", "consecutive": int}
        self.state_map = {}

    def update(self, track_id: int, zone_id: str, currently_inside: bool) -> str:
        """
        Updates the track state for a specific zone and returns an event if a transition is confirmed.
        Returns:
            "ZONE_ENTER"
            "ZONE_EXIT"
            None (no transition confirmed)
        """
        key = (track_id, zone_id)
        
        # Initialize if new track/zone pairing
        if key not in self.state_map:
            self.state_map[key] = {
                "status": "OUTSIDE",
                "consecutive": 0
            }

        state = self.state_map[key]

        # Check for state changes or persistence
        if currently_inside and state["status"] == "OUTSIDE":
            state["consecutive"] += 1
            if state["consecutive"] >= self.required_consecutive:
                state["status"] = "INSIDE"
                state["consecutive"] = 0
                return "ZONE_ENTER"
        
        elif not currently_inside and state["status"] == "INSIDE":
            state["consecutive"] += 1
            if state["consecutive"] >= self.required_consecutive:
                state["status"] = "OUTSIDE"
                state["consecutive"] = 0
                return "ZONE_EXIT"
        
        else:
            # Reverted back or remained stable, reset consecutive count
            state["consecutive"] = 0

        return None
