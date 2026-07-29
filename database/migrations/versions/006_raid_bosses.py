"""add raid_bosses and global raid_boss_timers

Revision ID: 006
Revises: 005
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raid_bosses",
        sa.Column("external_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("map_x", sa.Float(), nullable=True),
        sa.Column("map_y", sa.Float(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("respawn_raw", sa.String(120), nullable=True),
        sa.Column("respawn_min_sec", sa.Integer(), nullable=True),
        sa.Column("respawn_max_sec", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("wiki_url", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_raid_bosses_name", "raid_bosses", ["name"])
    op.create_index("ix_raid_bosses_level", "raid_bosses", ["level"])

    op.create_table(
        "raid_boss_timers",
        sa.Column("boss_external_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("killed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("set_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["boss_external_id"], ["raid_bosses.external_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["set_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Timers are shared, so the section stops being admin-only. Already-seeded
    # rows keep their old value, hence the explicit flip.
    op.execute(
        """
        UPDATE role_permissions SET allowed = true
        WHERE role = 'user' AND permission = 'nav.raid_bosses'
        """
    )


def downgrade() -> None:
    op.drop_table("raid_boss_timers")
    op.drop_index("ix_raid_bosses_level", table_name="raid_bosses")
    op.drop_index("ix_raid_bosses_name", table_name="raid_bosses")
    op.drop_table("raid_bosses")
