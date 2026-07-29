"""drop analytics blobs no UI reads (about 5 MB); source files stay on disk

Revision ID: 012
Revises: 011
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DORMANT_KEYS = ("craft_trees", "c_grade_farm", "d_grade_farm", "leveling_routes")


def upgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in DORMANT_KEYS)
    op.execute(f"DELETE FROM analytics_datasets WHERE dataset_key IN ({keys})")


def downgrade() -> None:
    # Blobs come back by re-running scripts/import_datasets.py with those keys.
    pass
