"""list_trades outlier marking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.market_service import list_trades


def test_list_trades_marks_outlier_rows():
    entity_id = uuid.uuid4()
    outlier_id = uuid.uuid4()
    normal_id = uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)

    entity = SimpleNamespace(id=entity_id)
    all_records = [
        SimpleNamespace(id=normal_id, price=Decimal("1000"), side="sell", entity_id=entity_id),
        SimpleNamespace(id=uuid.uuid4(), price=Decimal("1100"), side="sell", entity_id=entity_id),
        SimpleNamespace(id=uuid.uuid4(), price=Decimal("1050"), side="sell", entity_id=entity_id),
        SimpleNamespace(id=uuid.uuid4(), price=Decimal("1020"), side="sell", entity_id=entity_id),
        SimpleNamespace(id=outlier_id, price=Decimal("111111"), side="sell", entity_id=entity_id),
    ]
    outlier_row = SimpleNamespace(
        id=outlier_id,
        recorded_at=now,
        price=Decimal("111111"),
        quantity=1,
        side="sell",
        soul_crystal=None,
        rarity=None,
        armor_class=None,
        sealed=None,
        enchant_level=None,
    )
    normal_row = SimpleNamespace(
        id=normal_id,
        recorded_at=now,
        price=Decimal("1000"),
        quantity=1,
        side="sell",
        soul_crystal=None,
        rarity=None,
        armor_class=None,
        sealed=None,
        enchant_level=None,
    )

    db = MagicMock()
    db.get.return_value = entity
    db.scalar.return_value = 2
    exec_result = MagicMock()
    exec_result.all.return_value = [
        (outlier_row, "sadqgez"),
        (normal_row, "seller2"),
    ]
    db.execute.return_value = exec_result

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.market_service.fetch_records",
            lambda *_args, **_kwargs: (all_records, {}),
        )
        mp.setattr(
            "services.market_service.resolve_time_range",
            lambda *_args, **_kwargs: (now, now),
        )
        response = list_trades(
            db,
            entity_id=entity_id,
            side="sell",
            period="1d",
            from_date=None,
            to_date=None,
            search=None,
            sort_by="recorded_at",
            sort_order="desc",
            page=1,
            limit=50,
        )

    assert response.total == 2
    by_id = {item.id: item for item in response.items}
    assert by_id[outlier_id].is_outlier is True
    assert by_id[normal_id].is_outlier is False
