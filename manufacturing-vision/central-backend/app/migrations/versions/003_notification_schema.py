"""Add notification_channels and notification_rules tables

Revision ID: 003
Revises: 002
Create Date: 2026-04-05

Creates two tables for Phase 9 (Outbound Alert Notifications):
  notification_channels — where to send alerts (Slack, webhook, email)
  notification_rules    — when to trigger a channel (event_type + zone_id filter)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),    # "slack" | "webhook" | "email"
        sa.Column("config", sa.Text, nullable=False),  # JSON blob: {"url": "..."} etc.
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notification_rules",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("channel_id", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),  # "PPE_VIOLATION"|"ZONE_ENTER"|"ZONE_EXIT"|"*"
        sa.Column("zone_id", sa.Text),                      # NULL = match any zone
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_notification_rules_channel_id", "notification_rules", ["channel_id"])
    op.create_index("ix_notification_rules_active", "notification_rules", ["active"])


def downgrade() -> None:
    op.drop_index("ix_notification_rules_active", "notification_rules")
    op.drop_index("ix_notification_rules_channel_id", "notification_rules")
    op.drop_table("notification_rules")
    op.drop_table("notification_channels")
