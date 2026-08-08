"""craft_items.npc_buy for NG/D gear shop price

Revision ID: 025
Revises: 024
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("craft_items", sa.Column("npc_buy", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("craft_items", "npc_buy")
