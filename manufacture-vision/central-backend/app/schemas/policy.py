import json
from datetime import datetime

from pydantic import BaseModel, field_validator


class PolicyIn(BaseModel):
    zone_id: str
    required_ppe: list[str]


class PolicyOut(BaseModel):
    id: str
    zone_id: str
    required_ppe: list[str] | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("required_ppe", mode="before")
    @classmethod
    def _parse_json(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v
