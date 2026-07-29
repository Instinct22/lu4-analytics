"""make (entity_type, external_id) unique so craft tables can join wiki entities

Revision ID: 010
Revises: 009
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_wiki_entities_type_external_id",
        "wiki_entities",
        ["entity_type", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_wiki_entities_type_external_id", "wiki_entities", type_="unique")
