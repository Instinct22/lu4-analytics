"""Tests for offline craft catalog category rules."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from craft_catalog.categories import apply_categories, resolve_category  # noqa: E402


def test_robe_maps_to_magic():
    assert resolve_category("Armor / Robe / Upper Body") == "armors/magic"


def test_heavy_and_light_armor():
    assert resolve_category("Armor / Heavy / Upper Body") == "armors/heavy"
    assert resolve_category("Armor / Light / Full Body") == "armors/light"


def test_hair_accessory_stays_misc():
    assert resolve_category("Armor / None / Hair Accessory") == "armors/misc"


def test_weapon_sword():
    assert resolve_category("Weapon / Sword / One-handed") == "weapons/swords"


def test_soulshot_by_name():
    assert resolve_category("Other", "Soulshot (D-Grade)") == "other/soulshots"


def test_sealed_accessory_maps_to_jewelry():
    assert resolve_category("Accessory / Ring", "Sealed Phoenix Ring") == "other/jewelry"
    assert resolve_category("Accessory / Necklace", "Sealed Tateossian Necklace") == "other/jewelry"


def test_apply_categories_puts_sealed_jewelry_in_jewelry_bucket():
    payload = {
        "items": {
            "6325": {
                "id": 6325,
                "name": "Sealed Phoenix Ring",
                "grade": "A",
                "type": "Accessory / Ring",
            },
            "100": {
                "id": 100,
                "name": "Ring of Devotion",
                "grade": "D",
                "type": "Accessory / Ring",
            },
        },
        "byProduct": {"6325": [{"recipe_id": 1}], "100": [{"recipe_id": 2}]},
        "sets": {},
    }
    apply_categories(payload)
    jewelry = payload["categories"]["other"]["jewelry"]
    assert 6325 in jewelry
    assert 100 in jewelry
    assert "sealed" not in payload["categories"]["other"]


def test_apply_categories_builds_magic_bucket():
    payload = {
        "items": {
            "434": {
                "id": 434,
                "name": "White Tunic",
                "grade": "D",
                "type": "Armor / Robe / Upper Body",
            }
        },
        "byProduct": {"434": [{"recipe_id": 999}]},
        "sets": {},
    }
    apply_categories(payload)
    assert payload["items"]["434"]["category"] == "armors/magic"
    assert payload["categories"]["armors"]["magic"]["D"] == [434]
