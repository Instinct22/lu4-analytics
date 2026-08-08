"""raid_boss_notes: shared comment per raid boss

Revision ID: 024
Revises: 023
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raid_boss_notes",
        sa.Column("boss_external_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["boss_external_id"], ["raid_bosses.external_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("raid_boss_notes")
