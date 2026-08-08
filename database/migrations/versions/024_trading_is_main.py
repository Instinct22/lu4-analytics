"""trading_characters: is_main flag for bank↔warehouse sync

Revision ID: 024
Revises: 023
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trading_characters",
        sa.Column(
            "is_main",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_trading_characters_is_main",
        "trading_characters",
        ["is_main"],
    )


def downgrade() -> None:
    op.drop_index("ix_trading_characters_is_main", table_name="trading_characters")
    op.drop_column("trading_characters", "is_main")
