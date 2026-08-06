"""Trading inventory service: character CRUD, snapshots, adena totals."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from schemas.trading_inventory import (
    CharacterCreate,
    CharacterUpdate,
    InventoryLineIn,
    InventoryScanItem,
    InventoryScanRequest,
)
from services import trading_service


def _char(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        kind="bank",
        nick="Banker",
        clean_adena=Decimal("100"),
        master_coin=Decimal("0"),
        master_coin_price=Decimal("0"),
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
        master_coin=Decimal("3"),
        master_coin_price=Decimal("100"),
        items=[
            _line(quantity=2, unit_price=Decimal("100")),
            _line(quantity=1, unit_price=Decimal("50")),
        ],
    )
    out = trading_service._character_out(char)
    assert out.adena_in_items == Decimal("250")
    assert out.buy_cost == Decimal("0")
    assert out.master_coin_adena == Decimal("300")
    assert out.total_adena == Decimal("1550")  # 1000 + 250 + 300
    assert out.master_coin == Decimal("3")
    assert out.master_coin_price == Decimal("100")
    assert len(out.sell_items) == 2
    assert out.items[0].line_total == Decimal("200")
    assert out.items[0].catalog_matched is True


def test_character_out_unmatched_flag():
    char = _char(items=[_line(item_external_id=-42, item_name="Unknown Thing")])
    out = trading_service._character_out(char)
    assert out.sell_items[0].catalog_matched is False


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
        master_coin=Decimal("2"),
        master_coin_price=Decimal("50"),
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
    assert row["master_coin"] == "2"
    assert row["master_coin_price"] == "50"
    assert row["master_coin_adena"] == "100"
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
        master_coin=Decimal("9"),
        master_coin_price=Decimal("200"),
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
    assert body.master_coin == Decimal("9")
    assert body.master_coin_price == Decimal("200")


def test_custom_item_id_is_negative_and_stable():
    a = trading_service._custom_item_id("Weird Item")
    b = trading_service._custom_item_id("Weird Item")
    c = trading_service._custom_item_id("Other")
    assert a < 0
    assert a == b
    assert a != c


def test_is_wallet_item_name():
    assert trading_service._is_wallet_item_name("Adena")
    assert trading_service._is_wallet_item_name("Master Coin")
    assert trading_service._is_wallet_item_name("mastercoin")
    assert not trading_service._is_wallet_item_name("Coal")


def test_upsert_inventory_scan_creates_and_snapshots(monkeypatch):
    from models.trading import TradingSnapshot

    snap = TradingSnapshot(
        id=uuid.uuid4(),
        created_by_user_id=None,
        label="auto: inventory-scan Hero",
        payload={"characters": []},
    )

    char_holder: dict = {}

    def fake_create_snapshot(db, user_id=None, label=None):
        assert label == "auto: inventory-scan Hero"
        assert user_id is None
        return snap

    def fake_find(_db, nick):
        assert nick == "Hero"
        return None

    def fake_resolve(_db, raw_name):
        if raw_name == "Coal":
            return 1870, "Coal", True
        return trading_service._custom_item_id(raw_name), raw_name, False

    def fake_prices(_db, ids):
        return {1870: Decimal("12")}

    monkeypatch.setattr(trading_service, "create_snapshot", fake_create_snapshot)
    monkeypatch.setattr(trading_service, "_find_character_by_nick", fake_find)
    monkeypatch.setattr(trading_service, "_resolve_inventory_item", fake_resolve)
    monkeypatch.setattr(trading_service, "_unit_prices_for_ids", fake_prices)

    db = MagicMock()
    db.scalar.return_value = 0

    def capture_add(obj):
        if hasattr(obj, "nick"):
            char_holder["char"] = obj
            obj.items = []

    db.add.side_effect = capture_add

    def scalars_side_effect(*_args, **_kwargs):
        result = MagicMock()

        def one():
            char = char_holder["char"]
            if not hasattr(char, "items") or char.items is None:
                char.items = []
            return char

        result.one.side_effect = one
        result.first.return_value = None
        result.all.return_value = []
        return result

    db.scalars.side_effect = scalars_side_effect

    body = InventoryScanRequest(
        name="Hero",
        adena=Decimal("500000"),
        master_coin=Decimal("12"),
        items=[
            InventoryScanItem(name="Coal", count=100),
            InventoryScanItem(name="Unknown Gizmo", count=2),
            InventoryScanItem(name="Adena", count=999),  # wallet — skipped
        ],
    )
    resp = trading_service.upsert_inventory_scan(db, body)
    assert resp.created is True
    assert resp.snapshot_id == snap.id
    assert resp.matched_count == 1
    assert resp.unmatched_count == 1
    assert resp.character.clean_adena == Decimal("500000")
    assert resp.character.master_coin == Decimal("12")
    assert resp.character.nick == "Hero"
    assert len(resp.character.sell_items) == 2
    assert any(not i.catalog_matched for i in resp.character.sell_items)
    assert any(i.catalog_matched and i.item_name == "Coal" for i in resp.character.sell_items)


def test_upsert_inventory_scan_overwrites_existing(monkeypatch):
    snap_id = uuid.uuid4()
    snap = SimpleNamespace(id=snap_id)

    buy_line = _line(
        id=uuid.uuid4(),
        item_external_id=100,
        item_name="Buy Me",
        quantity=1,
        unit_price=Decimal("5"),
        list_kind="buy",
    )
    old_sell = _line(
        id=uuid.uuid4(),
        item_external_id=200,
        item_name="Old Sell",
        quantity=9,
        unit_price=Decimal("1"),
        list_kind="sell",
    )
    char = _char(
        id=uuid.uuid4(),
        kind="merchant",
        nick="Hero",
        clean_adena=Decimal("1"),
        master_coin=Decimal("1"),
        trade_mode="buy",
        description="keep me",
        items=[old_sell, buy_line],
    )

    monkeypatch.setattr(
        trading_service,
        "create_snapshot",
        lambda *a, **k: snap,
    )
    monkeypatch.setattr(trading_service, "_find_character_by_nick", lambda *_: char)
    monkeypatch.setattr(
        trading_service,
        "_resolve_inventory_item",
        lambda _db, name: (1870, "Coal", True),
    )
    monkeypatch.setattr(
        trading_service,
        "_unit_prices_for_ids",
        lambda *_: {1870: Decimal("3")},
    )

    db = MagicMock()
    reload = MagicMock()
    reload.one.return_value = char
    db.scalars.return_value = reload

    body = InventoryScanRequest(
        name="hero",
        adena=Decimal("42"),
        master_coin=Decimal("7"),
        items=[InventoryScanItem(name="Coal", count=5)],
    )
    resp = trading_service.upsert_inventory_scan(db, body)
    assert resp.created is False
    assert resp.snapshot_id == snap_id
    assert char.clean_adena == Decimal("42")
    assert char.master_coin == Decimal("7")
    assert char.description == "keep me"
    assert char.trade_mode == "buy"
    assert char.kind == "merchant"
    kinds = {getattr(i, "list_kind", "sell") for i in char.items}
    assert "buy" in kinds
    assert "sell" in kinds
    assert resp.matched_count == 1
    assert resp.unmatched_count == 0


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


def test_inventory_scan_requires_api_key(client, mock_db):
    r = client.post(
        "/api/trading/inventory-scan",
        json={"name": "Hero", "adena": 1, "master_coin": 0, "items": []},
    )
    assert r.status_code == 401


def test_inventory_scan_ok_with_api_key(client, mock_db, monkeypatch):
    from config import settings
    from schemas.trading_inventory import CharacterOut, InventoryScanResponse

    char_out = CharacterOut(
        id=uuid.uuid4(),
        kind="bank",
        nick="Hero",
        clean_adena=Decimal("10"),
        master_coin=Decimal("2"),
        master_coin_price=Decimal("100"),
        master_coin_adena=Decimal("200"),
        description=None,
        trade_mode="sell",
        adena_in_items=Decimal("0"),
        buy_cost=Decimal("0"),
        total_adena=Decimal("210"),
        sort_order=0,
        sell_items=[],
        buy_items=[],
        items=[],
    )
    snap_id = uuid.uuid4()

    def fake_upsert(_db, _body):
        return InventoryScanResponse(
            character=char_out,
            snapshot_id=snap_id,
            created=True,
            matched_count=0,
            unmatched_count=0,
        )

    monkeypatch.setattr(trading_service, "upsert_inventory_scan", fake_upsert)

    r = client.post(
        "/api/trading/inventory-scan",
        json={"name": "Hero", "adena": 10, "master_coin": 2, "items": []},
        headers={"X-Api-Key": settings.import_api_key},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["created"] is True
    assert data["character"]["nick"] == "Hero"
    assert data["character"]["master_coin"] == "2"
    assert data["snapshot_id"] == str(snap_id)
