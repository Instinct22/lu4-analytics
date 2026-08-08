"""Craft appraisal: base material walk + ranking helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.craft_service import (
    _collect_base_amounts,
    _resolve_main_unit_price,
    _resolve_market_unit_price,
    _shop_price,
    appraisal,
)


def test_collect_base_amounts_baked_children_not_remultiplied():
    """Baked children amounts are already scaled for the parent line amount."""
    tree = [
        {
            "id": 10,
            "amount": 20,
            "children": [{"id": 20, "amount": 5, "children": []}],
        }
    ]
    totals = _collect_base_amounts(tree, 1.0, {})
    assert totals == {20: 5.0}


def test_collect_base_amounts_expands_craftable_without_children():
    tree = [{"id": 50, "amount": 3, "children": []}]
    recipes = {
        50: [SimpleNamespace(tree=[{"id": 60, "amount": 4, "children": []}])],
    }
    totals = _collect_base_amounts(tree, 1.0, recipes)
    assert totals == {60: 12.0}


def test_resolve_main_unit_price_chain():
    assert _resolve_main_unit_price({"day_vwap": 100, "recent_vwap": 50, "npc_sell": 10}) == 100
    assert _resolve_main_unit_price({"day_vwap": None, "recent_vwap": 50, "npc_sell": 10}) == 50
    assert _resolve_main_unit_price({"day_vwap": None, "recent_vwap": None, "npc_sell": 10}) == 24.0
    assert _resolve_main_unit_price({}) is None
    assert _shop_price(100) == 240.0
    assert _shop_price(None) is None


def test_resolve_market_unit_price_ignores_npc():
    assert _resolve_market_unit_price({"day_vwap": None, "recent_vwap": None, "npc_sell": 10}) is None
    assert _resolve_market_unit_price({"day_vwap": None, "recent_vwap": 50, "npc_sell": 10}) == 50


def test_appraisal_empty_filter():
    db = MagicMock()
    empty = MagicMock()
    empty.all.return_value = []
    db.scalars.return_value = empty
    result = appraisal(db, grade="C", item_type="weapon")
    assert result["items"] == []
    assert result["grade"] == "C"
    assert result["type"] == "weapon"


def test_appraisal_builds_row_with_margins_per_variant():
    product = SimpleNamespace(
        external_id=100,
        name="Test Sword",
        grade="C",
        type="Weapon / Sword",
        category="weapons/swords",
        npc_sell=1000,
        stats={"crystals": 80},
    )
    recipe_a = SimpleNamespace(
        product_external_id=100,
        variant_index=0,
        yield_amount=1,
        rate=100,
        tree=[{"id": 200, "amount": 2, "children": []}],
    )
    recipe_b = SimpleNamespace(
        product_external_id=100,
        variant_index=1,
        yield_amount=1,
        rate=60,
        tree=[{"id": 200, "amount": 1, "children": []}],
    )

    db = MagicMock()
    r1, r2, r3, r4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    r1.all.return_value = [100]
    r2.all.return_value = [product]
    r3.all.return_value = [recipe_a, recipe_b]
    r4.all.return_value = [recipe_a, recipe_b]
    db.scalars.side_effect = [r1, r2, r3, r4]

    prices = {
        "100": {"day_vwap": 5000, "recent_vwap": None, "npc_sell": 1000},
        "200": {"day_vwap": 100, "recent_vwap": None, "npc_sell": None},
        "1459": {"day_vwap": 50, "recent_vwap": None, "npc_sell": None},
    }

    with patch("services.craft_service.prices_by_ids", return_value=prices):
        result = appraisal(db, grade="C", item_type="weapon", limit=10)

    assert len(result["items"]) == 2
    by_variant = {row["variant_index"]: row for row in result["items"]}
    a = by_variant[0]
    assert a["craft_cost"] == 200.0
    assert a["market_price"] == 5000.0
    assert a["shop_price"] == 2400.0
    assert a["crystal_price"] == 4000.0
    assert a["margin_market"] == 4800.0
    assert a["margin_shop"] == 2200.0
    assert a["margin_crystal"] == 3800.0
    b = by_variant[1]
    assert b["craft_cost"] == 100.0
    assert b["margin_market"] == 4900.0


def test_appraisal_market_dash_when_only_npc():
    product = SimpleNamespace(
        external_id=100,
        name="Untraded Sword",
        grade="C",
        type="Weapon / Sword",
        category="weapons/swords",
        npc_sell=1000,
        stats=None,
    )
    recipe = SimpleNamespace(
        product_external_id=100,
        variant_index=0,
        yield_amount=1,
        rate=100,
        tree=[{"id": 200, "amount": 2, "children": []}],
    )
    db = MagicMock()
    r1, r2, r3, r4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    r1.all.return_value = [100]
    r2.all.return_value = [product]
    r3.all.return_value = [recipe]
    r4.all.return_value = [recipe]
    db.scalars.side_effect = [r1, r2, r3, r4]
    prices = {
        "100": {"day_vwap": None, "recent_vwap": None, "npc_sell": 1000},
        "200": {"day_vwap": 100, "recent_vwap": None, "npc_sell": None},
    }
    with patch("services.craft_service.prices_by_ids", return_value=prices):
        result = appraisal(db, grade="C", item_type="weapon", limit=10)
    row = result["items"][0]
    assert row["market_price"] is None
    assert row["shop_price"] == 2400.0
    assert row["margin_market"] is None
    assert row["margin_shop"] == 2200.0
