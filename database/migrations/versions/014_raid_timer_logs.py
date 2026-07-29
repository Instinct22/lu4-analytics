"""raid timer audit log for primary admin

Revision ID: 014
Revises: 013
Create Date: 2026-07-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raid_timer_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("boss_external_id", sa.Integer(), nullable=False),
        sa.Column("boss_name", sa.String(160), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("killed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_raid_timer_logs_user_id", "raid_timer_logs", ["user_id"])
    op.create_index("ix_raid_timer_logs_username", "raid_timer_logs", ["username"])
    op.create_index("ix_raid_timer_logs_boss_external_id", "raid_timer_logs", ["boss_external_id"])
    op.create_index("ix_raid_timer_logs_logged_at", "raid_timer_logs", ["logged_at"])


def downgrade() -> None:
    op.drop_index("ix_raid_timer_logs_logged_at", table_name="raid_timer_logs")
    op.drop_index("ix_raid_timer_logs_boss_external_id", table_name="raid_timer_logs")
    op.drop_index("ix_raid_timer_logs_username", table_name="raid_timer_logs")
    op.drop_index("ix_raid_timer_logs_user_id", table_name="raid_timer_logs")
    op.drop_table("raid_timer_logs")
