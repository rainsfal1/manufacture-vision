import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Float, Index, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_ts_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_id: Mapped[str | None] = mapped_column(Text)
    track_id: Mapped[int | None] = mapped_column(Integer)
    zone_id: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[str | None] = mapped_column(Text)
    missing_ppe: Mapped[str | None] = mapped_column(Text)
    clip_ref: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_events_event_ts_ms", "event_ts_ms"),
        Index("ix_events_zone_id", "zone_id"),
        Index("ix_events_event_type", "event_type"),
    )
