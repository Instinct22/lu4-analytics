"""Trading inventory service: character CRUD, snapshots, adena totals."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from schemas.trading_inventory import CharacterCreate, CharacterUpdate, InventoryLineIn
from services import trading_service


def _char(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        kind="bank",
        nick="Banker",
        clean_adena=Decimal("100"),
        description=None,
        trade_mode="sell",
        sort_order=0,
        updated_at=None,
        items=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _line(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        item_external_id=57,
        item_name="Adena",
        quantity=2,
        unit_price=Decimal("50"),
        list_kind="sell",
        sort_order=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_character_out_computes_adena_totals():
    char = _char(
        clean_adena=Decimal("1000"),
        items=[
            _line(quantity=2, unit_price=Decimal("100")),
            _line(quantity=1, unit_price=Decimal("50")),
        ],
    )
    out = trading_service._character_out(char)
    assert out.adena_in_items == Decimal("250")
    assert out.buy_cost == Decimal("0")
    assert out.total_adena == Decimal("1250")
    assert len(out.sell_items) == 2
    assert out.items[0].line_total == Decimal("200")


def test_merchant_buy_mode_subtracts_cost():
    char = _char(
        kind="merchant",
        trade_mode="buy",
        clean_adena=Decimal("1000"),
        items=[
            _line(list_kind="sell", quantity=1, unit_price=Decimal("100")),
            _line(list_kind="buy", quantity=2, unit_price=Decimal("200")),
        ],
    )
    out = trading_service._character_out(char)
    assert out.trade_mode == "buy"
    assert out.adena_in_items == Decimal("100")
    assert out.buy_cost == Decimal("400")
    assert out.total_adena == Decimal("700")  # 1000 + 100 - 400
    assert len(out.buy_items) == 1
    assert len(out.items) == 1
    assert out.items[0].unit_price == Decimal("200")


def test_create_character_rejects_empty_nick():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        trading_service.create_character(
            db,
            CharacterCreate(kind="bank", nick="   "),
            uuid.uuid4(),
        )
    assert exc.value.status_code == 400


def test_snapshot_payload_shape():
    char = _char(
        id=uuid.uuid4(),
        kind="merchant",
        nick="Trader",
        clean_adena=Decimal("10"),
        description="shop",
        trade_mode="sell",
        items=[_line(item_external_id=4037, item_name="Coin", quantity=3, unit_price=Decimal("7"))],
    )
    db = MagicMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(trading_service, "list_characters", lambda _db: [trading_service._character_out(char)])
        payload = trading_service._snapshot_payload(db)
    assert len(payload["characters"]) == 1
    row = payload["characters"][0]
    assert row["nick"] == "Trader"
    assert row["kind"] == "merchant"
    assert row["trade_mode"] == "sell"
    assert row["sell_items"][0]["item_external_id"] == 4037
    assert "adena_in_items" in row


def test_update_character_not_found():
    db = MagicMock()
    result = MagicMock()
    result.first.return_value = None
    db.scalars.return_value = result
    with pytest.raises(HTTPException) as exc:
        trading_service.update_character(
            db,
            uuid.uuid4(),
            CharacterUpdate(clean_adena=Decimal("0"), sell_items=[], buy_items=[]),
            uuid.uuid4(),
        )
    assert exc.value.status_code == 404


def test_get_snapshot_not_found():
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        trading_service.get_snapshot(db, uuid.uuid4())
    assert exc.value.status_code == 404


def test_item_catalog_resources_first(monkeypatch):
    from schemas.trading_inventory import ItemCatalogHit

    def fake_resources(_db):
        return {
            "materials": [
                {"id": 1864, "name": "Stem"},
                {"id": 1865, "name": "Varnish"},
            ]
        }

    monkeypatch.setattr(trading_service.craft_service, "resource_materials", fake_resources)

    wiki_rows = [
        (1864, "Stem"),
        (1, "Adena"),
        (57, "Adena Pack"),
        (4037, "Master Coin"),
    ]
    db = MagicMock()
    db.execute.return_value.all.return_value = wiki_rows

    catalog = trading_service.item_catalog(db)
    assert all(isinstance(row, ItemCatalogHit) for row in catalog)
    assert catalog[0].group == "resource"
    resource_ids = [row.external_id for row in catalog if row.group == "resource"]
    assert 1864 in resource_ids
    assert 1865 in resource_ids
    assert 4037 in resource_ids
    others = [row for row in catalog if row.group == "item"]
    assert all(row.external_id not in resource_ids for row in others)
    assert {row.external_id for row in others} == {1, 57}


def test_character_update_schema_accepts_lines():
    body = CharacterUpdate(
        clean_adena=Decimal("5"),
        description="hi",
        trade_mode="buy",
        sell_items=[],
        buy_items=[
            InventoryLineIn(
                item_external_id=1,
                item_name="Sword",
                quantity=4,
                unit_price=Decimal("12.5"),
            )
        ],
    )
    assert body.buy_items[0].quantity == 4
    assert body.trade_mode == "buy"


def test_trading_characters_requires_permission(client, mock_db, test_user):
    """Admin role without nav.trading gets 403."""
    from main import app
    from api.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db.scalars.return_value.all.return_value = []
    r = client.get("/api/trading/characters")
    assert r.status_code == 403


def test_trading_characters_ok_for_superadmin(client, mock_db):
    from datetime import datetime, timezone

    from api.deps import get_current_user, hash_password
    from main import app
    from models.user import User

    user = User(
        id=uuid.uuid4(),
        username="root",
        password_hash=hash_password("x"),
        role="superadmin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: user

    chars_result = MagicMock()
    chars_result.all.return_value = []
    mock_db.scalars.return_value = chars_result

    r = client.get("/api/trading/characters")
    assert r.status_code == 200
    assert r.json() == {"characters": []}
    app.dependency_overrides.clear()
