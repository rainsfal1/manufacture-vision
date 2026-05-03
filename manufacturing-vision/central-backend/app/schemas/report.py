from datetime import datetime
from pydantic import BaseModel


class SummaryBucket(BaseModel):
    period: str           # ISO date "2026-04-01", shift "2026-04-01 shift-1", or week "2026-W14"
    ppe_violations: int
    zone_enter: int
    zone_exit: int
    by_zone: dict[str, int]   # {"zone_A": 14}
    by_ppe: dict[str, int]    # {"helmet": 8, "vest": 6}


class SummaryOut(BaseModel):
    from_date: str
    to_date: str
    granularity: str
    buckets: list[SummaryBucket]
    totals: dict[str, int]    # {"ppe_violations": N}


class TrendPoint(BaseModel):
    ts: datetime
    count: int


class TrendOut(BaseModel):
    event_type: str
    interval: str
    series: list[TrendPoint]
