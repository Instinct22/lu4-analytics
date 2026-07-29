"""split the character dataset into races, classes and skills

Revision ID: 008
Revises: 007
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "character_races",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    op.create_table(
        "character_classes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(96), nullable=False),
        sa.Column("slug", sa.String(96), nullable=False, server_default=""),
        sa.Column("icon", sa.Text(), nullable=False, server_default=""),
        sa.Column("portrait", sa.Text(), nullable=False, server_default=""),
        sa.Column("race_id", sa.String(32), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["race_id"], ["character_races.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_character_classes_name", "character_classes", ["name"])
    op.create_index("ix_character_classes_race_id", "character_classes", ["race_id"])

    op.create_table(
        "character_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("icon", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(64), nullable=False, server_default=""),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_character_skills_name", "character_skills", ["name"])


def downgrade() -> None:
    op.drop_index("ix_character_skills_name", table_name="character_skills")
    op.drop_table("character_skills")
    op.drop_index("ix_character_classes_race_id", table_name="character_classes")
    op.drop_index("ix_character_classes_name", table_name="character_classes")
    op.drop_table("character_classes")
    op.drop_table("character_races")
