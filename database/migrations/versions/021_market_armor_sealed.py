"""market_records: armor_class + sealed variant attributes

Revision ID: 021
Revises: 020
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("market_records", sa.Column("armor_class", sa.String(length=32), nullable=True))
    op.add_column("market_records", sa.Column("sealed", sa.Boolean(), nullable=True))
    op.drop_index("ix_market_records_entity_variant", table_name="market_records")
    op.create_index(
        "ix_market_records_entity_variant",
        "market_records",
        ["entity_id", "soul_crystal", "rarity", "armor_class", "enchant_level", "sealed"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_records_entity_variant", table_name="market_records")
    op.drop_column("market_records", "sealed")
    op.drop_column("market_records", "armor_class")
    op.create_index(
        "ix_market_records_entity_variant",
        "market_records",
        ["entity_id", "soul_crystal", "rarity", "enchant_level"],
    )
