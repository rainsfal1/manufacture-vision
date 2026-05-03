"""Initial schema: events, zones, policies, audit_log

Revision ID: 001
Revises:
Create Date: 2026-04-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("event_ts_ms", sa.BigInteger, nullable=False),
        sa.Column("source_id", sa.Text),
        sa.Column("track_id", sa.Integer),
        sa.Column("zone_id", sa.Text),
        sa.Column("confidence", sa.Float),
        sa.Column("bbox", sa.Text),
        sa.Column("missing_ppe", sa.Text),
        sa.Column("clip_ref", sa.Text),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_events_event_ts_ms", "events", ["event_ts_ms"])
    op.create_index("ix_events_zone_id", "events", ["zone_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])

    op.create_table(
        "zones",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("zone_id", sa.Text, unique=True, nullable=False),
        sa.Column("polygon", sa.Text),
        sa.Column("required_ppe", sa.Text),
        sa.Column("camera_id", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("zone_id", sa.Text, nullable=False),
        sa.Column("required_ppe", sa.Text),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("actor", sa.Text),
        sa.Column("action", sa.Text),
        sa.Column("entity_type", sa.Text),
        sa.Column("entity_id", sa.Text),
        sa.Column("diff", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("policies")
    op.drop_table("zones")
    op.drop_index("ix_events_event_type", "events")
    op.drop_index("ix_events_zone_id", "events")
    op.drop_index("ix_events_event_ts_ms", "events")
    op.drop_table("events")
