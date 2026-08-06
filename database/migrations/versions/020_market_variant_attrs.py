"""market_records: soul crystal, rarity + enchant level variant attributes

Revision ID: 020
Revises: 019
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("market_records", sa.Column("soul_crystal", sa.String(length=32), nullable=True))
    op.add_column("market_records", sa.Column("rarity", sa.String(length=48), nullable=True))
    op.add_column("market_records", sa.Column("enchant_level", sa.Integer(), nullable=True))
    op.create_index(
        "ix_market_records_entity_variant",
        "market_records",
        ["entity_id", "soul_crystal", "rarity", "enchant_level"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_records_entity_variant", table_name="market_records")
    op.drop_column("market_records", "enchant_level")
    op.drop_column("market_records", "rarity")
    op.drop_column("market_records", "soul_crystal")
