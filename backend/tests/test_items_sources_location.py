"""Tests for filtering mob sources without wiki locations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from models.craft import CraftMaterialSource
from services.normalizers.craft import RESOURCES_META_KEY
from services.normalizers.items_encyclopedia import (
    _import_material_sources_from_encyclopedia,
    _sources_with_location,
    normalize_items_encyclopedia,
)
from tests.test_craft import RecordingSession, added_of


def test_sources_with_location_keeps_only_located_mobs():
    db = MagicMock()
    rows = [
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
    ]

    with patch(
        "services.normalizers.items_encyclopedia.npc_has_location",
        side_effect=lambda _db, npc_id: npc_id == 500,
    ):
        located = _sources_with_location(db, rows)

    assert [row["npc_id"] for row in located] == [500]


def test_import_material_sources_keeps_resource_with_zero_located_counts():
    db = RecordingSession()
    payload = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "items": {
            "30": {
                "id": 30,
                "name": "Stem",
                "grade": "NG",
                "category": "materials/other",
                "section": "other",
                "type": "Material",
                "drops": [
                    {
                        "npc_id": 21181,
                        "npc_name": "Lilim Assassin",
                        "npc_level": 66,
                        "npc_level_raw": "Lv. 66",
                        "amount": "1",
                        "chance": "0.01%",
                    }
                ],
                "spoils": [],
            },
        },
        "craft": {
            "byProduct": {
                "10": [
                    {
                        "tree": [
                            {"id": 30, "amount": 5, "children": []},
                            {"id": 30, "amount": 5, "children": []},
                            {"id": 30, "amount": 5, "children": []},
                            {"id": 30, "amount": 5, "children": []},
                            {"id": 30, "amount": 5, "children": []},
                        ]
                    }
                ]
            }
        },
    }

    with patch("services.normalizers.items_encyclopedia.npc_has_location", return_value=False):
        _import_material_sources_from_encyclopedia(db, payload)

    assert added_of(db, CraftMaterialSource) == []
    meta = next(row for row in db.added if getattr(row, "dataset_key", None) == RESOURCES_META_KEY)
    material = next(m for m in meta.payload["materials"] if m["id"] == 30)
    assert material["spoil_count"] == 0
    assert material["drop_count"] == 0


def test_normalize_items_encyclopedia_filters_payload_sources():
    db = RecordingSession()
    payload = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "item_count": 1,
        "section_counts": {"other": 1},
        "items": {
            "4052": {
                "id": 4052,
                "name": "Earring of Black Ore Piece",
                "grade": "NG",
                "section": "other",
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
        },
        "craft": {"byProduct": {}},
    }

    with (
        patch(
            "services.normalizers.items_encyclopedia.npc_has_location",
            side_effect=lambda _db, npc_id: npc_id == 500,
        ),
        patch("services.normalizers.items_encyclopedia._import_craft_from_encyclopedia"),
        patch("services.normalizers.items_encyclopedia._import_material_sources_from_encyclopedia"),
        patch("services.normalizers.items_encyclopedia._sync_wiki_names_from_encyclopedia", return_value=0),
        patch("services.normalizers.items_encyclopedia._refresh_wiki_item_name_normalized", return_value=0),
        patch("services.normalizers.items_encyclopedia.rematch_market_records", return_value=(0, [])),
        patch("services.normalizers.items_encyclopedia.recalculate_item_statistics"),
    ):
        normalize_items_encyclopedia(db, payload)

    from models.item_encyclopedia import ItemEncyclopedia

    row = next(item for item in added_of(db, ItemEncyclopedia) if item.external_id == 4052)
    assert [source["npc_id"] for source in row.payload["drops"]] == [500]
    assert row.payload["has_drop"] is True
    assert row.payload["has_spoil"] is False
