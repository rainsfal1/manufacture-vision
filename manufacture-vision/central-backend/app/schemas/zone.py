import json
from datetime import datetime

from pydantic import BaseModel, field_validator


class ZoneIn(BaseModel):
    zone_id: str
    polygon: list[list[float]] | None = None
    required_ppe: list[str] | None = None
    camera_id: str | None = None


class ZoneOut(BaseModel):
    id: str
    zone_id: str
    polygon: list[list[float]] | None
    required_ppe: list[str] | None
    camera_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("polygon", "required_ppe", mode="before")
    @classmethod
    def _parse_json(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v
