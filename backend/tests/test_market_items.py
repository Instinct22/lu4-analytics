"""Market item list deduplicates wiki variant entities to one canonical base."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.market_service import market_items
from tests.conftest import make_entity


def test_market_items_dedupes_same_normalized_name():
    base = make_entity(
        id=uuid.uuid4(),
        external_id=240,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )
    variant = make_entity(
        id=uuid.uuid4(),
        external_id=38195,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )

    rows = [
        SimpleNamespace(
            id=base.id,
            external_id=base.external_id,
            display_name=base.display_name,
            name_normalized=base.name_normalized,
            record_count=5,
        ),
        SimpleNamespace(
            id=variant.id,
            external_id=variant.external_id,
            display_name=variant.display_name,
            name_normalized=variant.name_normalized,
            record_count=3,
        ),
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = rows
    db.scalars.return_value.all.return_value = [base, variant]

    with patch(
        "services.market_service._pick_canonical_entity",
        return_value=base,
    ):
        result = market_items(db, q=None, limit=50)

    assert len(result.items) == 1
    assert result.items[0].id == base.id
    assert result.items[0].record_count == 8
