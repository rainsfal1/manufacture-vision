import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class ChannelIn(BaseModel):
    name: str
    type: Literal["slack", "webhook", "email"]
    config: dict


class ChannelOut(BaseModel):
    id: str
    name: str
    type: str
    config: dict
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("config", mode="before")
    @classmethod
    def _parse_config(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class RuleIn(BaseModel):
    channel_id: str
    event_type: str   # "PPE_VIOLATION" | "ZONE_ENTER" | "ZONE_EXIT" | "*"
    zone_id: str | None = None
    active: bool = True


class RuleOut(BaseModel):
    id: str
    channel_id: str
    event_type: str
    zone_id: str | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
