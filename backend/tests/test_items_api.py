"""API tests for item encyclopedia endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services import items_service


def test_catalog_light_shape():
    row = MagicMock()
    row.external_id = 6661
    row.name = "Earring of Orfen"
    row.grade = "C"
    row.type = "Accessory / Earring"
    row.section = "gear"
    row.other_subcategory = None
    row.icon = "accessory_earring_of_orfen_i00.png"
    row.url = "/lu4/item/6661-earring-of-orfen"
    row.payload = {
        "npc_sell": 650000,
        "stats": {"m_def": 63},
        "drops": [{"npc_id": 29014}],
        "craft": {"craftable": False},
    }

    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    db.scalar.return_value = None

    result = items_service.catalog(db, section="gear")
    assert result["items"][0]["id"] == 6661
    assert result["items"][0]["has_drop"] is True


def test_item_detail_returns_payload():
    row = MagicMock()
    row.external_id = 6661
    row.section = "gear"
    row.payload = {
        "id": 6661,
        "name": "Earring of Orfen",
        "drops": [{"npc_id": 29014, "npc_name": "Orfen"}],
        "spoils": [],
        "craft": {"craftable": True, "variants": [{"recipe_id": 1, "tree": []}]},
    }

    db = MagicMock()
    db.get.return_value = row

    detail = items_service.item_detail(db, 6661)
    assert detail is not None
    assert detail["name"] == "Earring of Orfen"
    assert detail["has_drop"] is True
    assert "drops" not in detail
    assert "spoils" not in detail
    assert detail["craft"] == {"craftable": True, "variants": []}


def test_browse_returns_gear_craft_slice():
    gear_row = MagicMock()
    gear_row.external_id = 10
    gear_row.name = "Bone Helmet"
    gear_row.grade = "D"
    gear_row.type = "Armor / Heavy / Head"
    gear_row.section = "gear"
    gear_row.other_subcategory = None
    gear_row.icon = None
    gear_row.payload = {"stats": {"p_def": 20}, "craft": {"craftable": True}}

    craft_item = MagicMock()
    craft_item.external_id = 10
    craft_item.name = "Bone Helmet"
    craft_item.grade = "D"
    craft_item.type = "Armor / Heavy / Head"
    craft_item.category = "armors/heavy"
    craft_item.set_name = "Bone Set"
    craft_item.npc_sell = 100
    craft_item.url = ""
    craft_item.is_recipe_scroll = False
    craft_item.stats = {"p_def": 20}

    craft_meta = MagicMock()
    craft_meta.payload = {
        "sets": {"Bone Set": [10]},
        "setMeta": {"Bone Set": {"name": "Bone Set", "grade": "D", "allMemberIds": [10]}},
        "itemIcons": {},
        "product_count": 1,
        "variant_count": 1,
    }

    enc_meta = MagicMock()
    enc_meta.payload = {"generated_at": "now", "item_count": 1}

    duals_row = MagicMock()
    duals_row.generated_at = None
    duals_row.payload = {"items": {}}

    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.side_effect = [
        [gear_row],  # gear catalog
        [craft_item],  # craft items for needed ids
        [10],  # craftable ids
    ]
    db.scalars.return_value = scalars_result

    meta_calls = {"n": 0}

    def scalar_side_effect(_stmt):
        meta_calls["n"] += 1
        if meta_calls["n"] == 1:
            return enc_meta
        if meta_calls["n"] == 2:
            return craft_meta
        return duals_row

    db.scalar.side_effect = scalar_side_effect

    result = items_service.browse(db)
    assert result["gear"]["items"][0]["id"] == 10
    assert "10" in result["craft"]["items"]
    assert result["craft"]["sets"]["Bone Set"] == [10]
    assert result["duals"] is not None
    assert result["craft"]["byProduct"] == {}


def test_item_sources_excludes_mobs_without_location():
    row = MagicMock()
    row.external_id = 4052
    row.payload = {
        "drops": [
            {
                "npc_id": 500,
                "npc_name": "Goblin",
                "npc_level": 12,
                "npc_level_raw": "Lv. 12",
                "amount": "1",
                "chance": "30%",
            },
            {
                "npc_id": 21181,
                "npc_name": "Lilim Assassin",
                "npc_level": 66,
                "npc_level_raw": "Lv. 66",
                "amount": "1",
                "chance": "0.01%",
            },
        ],
        "spoils": [],
    }

    db = MagicMock()
    db.get.return_value = row

    with patch(
        "services.items_service._npc_meta_lookup",
        return_value={500: {"locations": [{"name": "Gludio", "url": "/lu4/location/1"}]}},
    ):
        result = items_service.item_sources(db, 4052)

    assert result is not None
    assert [source["npc_id"] for source in result["drops"]] == [500]
    assert result["spoils"] == []
