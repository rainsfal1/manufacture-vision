import json
from datetime import datetime

from pydantic import BaseModel, computed_field


class EventOut(BaseModel):
    id: str
    event_type: str
    event_ts_ms: int
    source_id: str | None
    track_id: int | None
    zone_id: str | None
    confidence: float | None
    bbox: str | None
    missing_ppe: str | None
    clip_ref: str | None
    received_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def clip_key(self) -> str | None:
        """Extract the MinIO object key from clip_ref (stored as Python repr or JSON string)."""
        if not self.clip_ref:
            return None
        try:
            data = json.loads(self.clip_ref.replace("'", '"'))
            return data.get("key")
        except Exception:
            return self.clip_ref  # fallback: assume it's already a bare key


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int
    limit: int
    offset: int
