"""Add composite indexes for reporting queries

Revision ID: 002
Revises: 001
Create Date: 2026-04-05

Adds two composite indexes to the events table that make the Phase 8
reporting endpoints efficient:

  ix_events_type_ts  (event_type, event_ts_ms) — covers trend/export
                     queries that filter by type + time range
  ix_events_zone_ts  (zone_id, event_ts_ms)    — covers zone-scoped
                     summary and trend queries
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_events_type_ts", "events", ["event_type", "event_ts_ms"])
    op.create_index("ix_events_zone_ts", "events", ["zone_id", "event_ts_ms"])


def downgrade() -> None:
    op.drop_index("ix_events_zone_ts", "events")
    op.drop_index("ix_events_type_ts", "events")
