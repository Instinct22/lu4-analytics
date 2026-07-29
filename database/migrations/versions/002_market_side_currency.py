"""add market side and expand currency

Revision ID: 002
Revises: 001
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("market_records", sa.Column("side", sa.String(4), nullable=True))
    op.create_index("ix_market_records_entity_side_recorded", "market_records", ["entity_id", "side", "recorded_at"])
    op.alter_column("market_records", "currency", type_=sa.String(32), existing_type=sa.String(3))


def downgrade() -> None:
    op.alter_column("market_records", "currency", type_=sa.String(3), existing_type=sa.String(32))
    op.drop_index("ix_market_records_entity_side_recorded", table_name="market_records")
    op.drop_column("market_records", "side")
