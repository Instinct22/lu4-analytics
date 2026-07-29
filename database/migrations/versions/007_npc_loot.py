"""add npc_loot so spoil/drop tables are not parsed from HTML per request

Revision ID: 007
Revises: 006
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "npc_loot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("npc_external_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("item_external_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("item_grade", sa.String(16), nullable=False, server_default=""),
        sa.Column("item_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("amount", sa.String(64), nullable=False, server_default=""),
        sa.Column("chance_text", sa.String(32), nullable=False, server_default=""),
        sa.Column("chance_val", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_npc_loot_npc_kind", "npc_loot", ["npc_external_id", "kind"])
    op.create_index("ix_npc_loot_item", "npc_loot", ["item_external_id"])


def downgrade() -> None:
    op.drop_index("ix_npc_loot_item", table_name="npc_loot")
    op.drop_index("ix_npc_loot_npc_kind", table_name="npc_loot")
    op.drop_table("npc_loot")
