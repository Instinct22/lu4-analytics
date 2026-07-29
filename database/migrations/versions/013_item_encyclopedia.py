"""item encyclopedia table

Revision ID: 013
Revises: 012
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_encyclopedia",
        sa.Column("external_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("section", sa.String(16), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("grade", sa.String(16), nullable=False, server_default=""),
        sa.Column("type", sa.String(96), nullable=False, server_default=""),
        sa.Column("other_subcategory", sa.String(32), nullable=True),
        sa.Column("icon", sa.String(128), nullable=True),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_item_encyclopedia_section", "item_encyclopedia", ["section"])
    op.create_index("ix_item_encyclopedia_name", "item_encyclopedia", ["name"])
    op.create_index("ix_item_encyclopedia_grade", "item_encyclopedia", ["grade"])
    op.create_index(
        "ix_item_encyclopedia_other_subcategory", "item_encyclopedia", ["other_subcategory"]
    )


def downgrade() -> None:
    op.drop_index("ix_item_encyclopedia_other_subcategory", table_name="item_encyclopedia")
    op.drop_index("ix_item_encyclopedia_grade", table_name="item_encyclopedia")
    op.drop_index("ix_item_encyclopedia_name", table_name="item_encyclopedia")
    op.drop_index("ix_item_encyclopedia_section", table_name="item_encyclopedia")
    op.drop_table("item_encyclopedia")
