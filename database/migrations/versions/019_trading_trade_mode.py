"""Merchant trade_mode and inventory list_kind

Revision ID: 019
Revises: 018
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trading_characters",
        sa.Column("trade_mode", sa.String(16), nullable=False, server_default="sell"),
    )
    op.add_column(
        "trading_inventory_lines",
        sa.Column("list_kind", sa.String(16), nullable=False, server_default="sell"),
    )
    op.create_index(
        "ix_trading_inventory_lines_list_kind",
        "trading_inventory_lines",
        ["list_kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_trading_inventory_lines_list_kind", table_name="trading_inventory_lines")
    op.drop_column("trading_inventory_lines", "list_kind")
    op.drop_column("trading_characters", "trade_mode")
