"""Weapon/armor/jewelry variants resolve to one canonical base + attrs."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import services.import_service as import_service
from services.import_service import ResolvedMarketItem, rematch_market_records, resolve_market_item
from services.name_matching import parse_market_name
from services.variant_lexicon import classify_market_name
from tests.conftest import make_entity


# --- pure parsing -----------------------------------------------------------


def test_parse_clean_name():
    parsed = parse_market_name("Conjurer's Knife")
    assert parsed.enchant_level is None
    assert parsed.soul_crystal is None
    assert parsed.base_normalized == "conjurers knife"
    assert parsed.full_normalized == "conjurers knife"


def test_parse_soul_ability_suffix():
    parsed = parse_market_name("Conjurers Knife Acumen")
    assert parsed.soul_crystal == "Acumen"
    assert parsed.base_name == "Conjurers Knife"
    assert parsed.base_normalized == "conjurers knife"
    assert parsed.full_normalized == "conjurers knife acumen"


def test_parse_enchant_prefix_and_soul_ability():
    parsed = parse_market_name("+3 Conjurers Knife Acumen")
    assert parsed.enchant_level == 3
    assert parsed.soul_crystal == "Acumen"
    assert parsed.base_normalized == "conjurers knife"


def test_parse_enchant_only():
    parsed = parse_market_name("+5 Conjurer's Knife")
    assert parsed.enchant_level == 5
    assert parsed.soul_crystal is None
    assert parsed.base_normalized == "conjurers knife"


def test_parse_prefers_longest_soul_ability():
    parsed = parse_market_name("Some Staff Magic Focus")
    assert parsed.soul_crystal == "Magic Focus"
    assert parsed.base_name == "Some Staff"


def test_parse_rare_variant_with_soul_ability():
    parsed = parse_market_name("+3 Halberd - Lightning Haste")
    assert parsed.enchant_level == 3
    assert parsed.rarity == "Lightning"
    assert parsed.soul_crystal == "Haste"
    assert parsed.base_name == "Halberd"
    assert parsed.base_normalized == "halberd"


def test_parse_rare_variant_without_soul_ability():
    parsed = parse_market_name("Halberd - Lightning")
    assert parsed.rarity == "Lightning"
    assert parsed.soul_crystal is None
    assert parsed.base_name == "Halberd"


def test_parse_armor_unseal_without_dash():
    parsed = classify_market_name("Zubei's Boots Heavy Armor")
    assert parsed.armor_class == "heavy"
    assert parsed.sealed is False
    assert parsed.base_name == "Zubei's Boots"
    assert parsed.base_normalized == "zubeis boots"


def test_parse_sealed_jewelry_with_enchant():
    parsed = classify_market_name("+3 Sealed Phoenix Ring")
    assert parsed.enchant_level == 3
    assert parsed.sealed is True
    assert parsed.base_name == "Phoenix Ring"
    assert parsed.full_normalized == "sealed phoenix ring"


def test_parse_does_not_strip_standalone_robe_piece():
    """Whole pieces named '... Robe' must not lose the word Robe as armor_class."""
    parsed = classify_market_name("Avadon Robe")
    assert parsed.armor_class is None
    assert parsed.base_name == "Avadon Robe"


# --- resolution -------------------------------------------------------------


def _wiki_scalars(sequences: list[list]):
    """Return successive WikiEntity result sets; everything else is empty."""
    state = {"i": 0}

    def handler(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        if entity.__name__ == "WikiEntity":
            idx = min(state["i"], len(sequences) - 1)
            state["i"] += 1
            rows = sequences[idx]
            return SimpleNamespace(all=lambda r=rows: list(r))
        return SimpleNamespace(all=lambda: [])

    return handler


def _weapon_enc(**payload):
    return SimpleNamespace(
        type="Weapon / Sword",
        section="gear",
        payload={"item_modifiers": payload} if payload else {"item_modifiers": {}},
        name="x",
    )


def test_resolve_soul_ability_variant_maps_to_canonical_base():
    base = make_entity(
        id=uuid.uuid4(),
        entity_key="item:240",
        external_id=240,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )
    variant = make_entity(
        id=uuid.uuid4(),
        entity_key="item:38195",
        external_id=38195,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )

    db = MagicMock()
    db.scalars.side_effect = _wiki_scalars([[variant, base]])
    db.execute.return_value = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(external_id=240, section="gear"),
            SimpleNamespace(external_id=38195, section="excluded"),
        ]
    )
    db.get.return_value = _weapon_enc(soul_crystals=[{"name": "Acumen"}, {"name": "Focus"}])

    resolved = resolve_market_item(db, "Conjurers Knife Acumen")
    assert resolved.entity is base
    assert resolved.enchant_level is None
    assert resolved.soul_crystal == "Acumen"
    assert resolved.rarity is None


def test_resolve_enchanted_soul_ability_variant():
    base = make_entity(
        id=uuid.uuid4(),
        entity_key="item:240",
        external_id=240,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )
    db = MagicMock()
    db.scalars.side_effect = _wiki_scalars([[base]])
    db.get.return_value = _weapon_enc(soul_crystals=[{"name": "Acumen"}])

    resolved = resolve_market_item(db, "+3 Conjurers Knife Acumen")
    assert resolved.entity is base
    assert resolved.enchant_level == 3
    assert resolved.soul_crystal == "Acumen"
    assert resolved.rarity is None


def test_resolve_rare_variant_maps_to_canonical_base():
    base = make_entity(
        id=uuid.uuid4(),
        entity_key="item:900",
        external_id=900,
        name="Halberd",
        display_name="Halberd",
        name_normalized="halberd",
    )
    db = MagicMock()
    db.scalars.side_effect = _wiki_scalars([[base]])
    db.get.return_value = _weapon_enc(rarity=[{"name": "Lightning", "sa": "Haste"}])

    resolved = resolve_market_item(db, "+3 Halberd - Lightning Haste")
    assert resolved.entity is base
    assert resolved.enchant_level == 3
    assert resolved.rarity == "Lightning"
    assert resolved.soul_crystal == "Haste"


def test_resolve_clean_item_has_no_variant_attrs():
    base = make_entity(
        id=uuid.uuid4(),
        entity_key="item:240",
        external_id=240,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )
    db = MagicMock()
    db.scalars.side_effect = _wiki_scalars([[base]])
    db.get.return_value = _weapon_enc()

    resolved = resolve_market_item(db, "Conjurer's Knife")
    assert resolved.entity is base
    assert resolved.enchant_level is None
    assert resolved.soul_crystal is None
    assert resolved.rarity is None


def test_resolve_rejects_unsupported_soul_ability():
    """A trailing SA word not listed on the base must not be stripped blindly."""
    base = make_entity(
        id=uuid.uuid4(),
        entity_key="item:240",
        external_id=240,
        name="Conjurer's Knife",
        display_name="Conjurer's Knife",
        name_normalized="conjurers knife",
    )
    db = MagicMock()
    db.scalars.side_effect = _wiki_scalars([[base], []])
    db.get.return_value = _weapon_enc(soul_crystals=[])

    resolved = resolve_market_item(db, "Conjurers Knife Acumen")
    assert resolved.soul_crystal is None


def test_resolve_armor_unseal_folds_to_sealed_base():
    sealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:554",
        external_id=554,
        name="Sealed Zubei's Boots",
        display_name="Sealed Zubei's Boots",
        name_normalized="sealed zubeis boots",
    )
    unsealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:600",
        external_id=600,
        name="Zubei's Boots",
        display_name="Zubei's Boots",
        name_normalized="zubeis boots",
    )
    db = MagicMock()
    # base lookup → unsealed; fold via sealed_id; prefer-gear re-pick
    db.scalars.side_effect = _wiki_scalars([[unsealed], [sealed]])
    db.get.return_value = SimpleNamespace(
        type="Armor / Heavy / Boots",
        section="gear",
        name="Zubei's Boots",
        payload={"sealed_group": {"sealed_id": 554, "base_name": "Zubei's Boots"}},
    )
    db.scalar.side_effect = [sealed]  # _wiki_item_by_external_id

    resolved = resolve_market_item(db, "Zubei's Boots Heavy Armor")
    assert resolved.entity is sealed
    assert resolved.armor_class == "heavy"
    assert resolved.sealed is False
    assert resolved.soul_crystal is None


def test_resolve_unsealed_jewelry_folds_to_sealed_base():
    sealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:901",
        external_id=901,
        name="Sealed Phoenix Ring",
        display_name="Sealed Phoenix Ring",
        name_normalized="sealed phoenix ring",
    )
    db = MagicMock()
    # bare miss → sealed twin → prefer-gear re-pick
    db.scalars.side_effect = _wiki_scalars([[], [sealed], [sealed]])
    db.get.return_value = SimpleNamespace(
        type="Accessory / Ring",
        section="gear",
        name="Sealed Phoenix Ring",
        payload={"unseal_variants": [{"name": "Phoenix Ring"}]},
    )

    resolved = resolve_market_item(db, "+2 Phoenix Ring")
    assert resolved.entity is sealed
    assert resolved.enchant_level == 2
    assert resolved.sealed is False
    assert resolved.armor_class is None


def test_resolve_sealed_jewelry_keeps_sealed_flag():
    sealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:901",
        external_id=901,
        name="Sealed Phoenix Ring",
        display_name="Sealed Phoenix Ring",
        name_normalized="sealed phoenix ring",
    )
    db = MagicMock()
    # full sealed lookup + prefer-gear re-pick by same normalized key
    db.scalars.side_effect = _wiki_scalars([[sealed], [sealed]])
    db.get.return_value = SimpleNamespace(
        type="Accessory / Ring",
        section="gear",
        name="Sealed Phoenix Ring",
        payload={},
    )

    resolved = resolve_market_item(db, "+3 Sealed Phoenix Ring")
    assert resolved.entity is sealed
    assert resolved.enchant_level == 3
    assert resolved.sealed is True


def test_resolve_jewelry_prefers_gear_sealed_over_excluded_duplicate():
    """Unsealed jewelry must fold onto the gear Sealed row, not excluded twin."""
    excluded_sealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:11582",
        external_id=11582,
        name="Sealed Phoenix Ring",
        display_name="Sealed Phoenix Ring",
        name_normalized="sealed phoenix ring",
    )
    gear_sealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:6325",
        external_id=6325,
        name="Sealed Phoenix Ring",
        display_name="Sealed Phoenix Ring",
        name_normalized="sealed phoenix ring",
    )
    unsealed = make_entity(
        id=uuid.uuid4(),
        entity_key="item:902",
        external_id=902,
        name="Phoenix Ring",
        display_name="Phoenix Ring",
        name_normalized="phoenix ring",
    )
    db = MagicMock()
    # 1) bare phoenix ring lookup  2) prefer-gear among sealed phoenix ring
    db.scalars.side_effect = _wiki_scalars([[unsealed], [excluded_sealed, gear_sealed]])
    db.execute.return_value = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(external_id=11582, section="excluded"),
            SimpleNamespace(external_id=6325, section="gear"),
        ]
    )
    db.get.return_value = SimpleNamespace(
        type="Accessory / Ring",
        section="excluded",
        name="Phoenix Ring",
        payload={"sealed_group": {"sealed_id": 11582, "base_name": "Phoenix Ring"}},
    )
    db.scalar.side_effect = [excluded_sealed]

    resolved = resolve_market_item(db, "Phoenix Ring")
    assert resolved.entity is gear_sealed
    assert resolved.sealed is False


# --- backfill ---------------------------------------------------------------


def test_rematch_backfills_variant_attributes():
    old_entity = uuid.uuid4()
    new_entity = make_entity(id=uuid.uuid4(), external_id=240, name_normalized="conjurers knife")

    record = SimpleNamespace(
        product_name_raw="Conjurers Knife Acumen",
        product_name_normalized="stale",
        entity_id=old_entity,
        soul_crystal=None,
        rarity=None,
        armor_class=None,
        sealed=None,
        enchant_level=None,
    )

    db = MagicMock()
    db.scalars.return_value = SimpleNamespace(all=lambda: [record])

    with patch.object(
        import_service,
        "resolve_market_item",
        return_value=ResolvedMarketItem(new_entity, 3, "Acumen", "Lightning", None, None),
    ):
        updated, affected = rematch_market_records(db)

    assert updated == 1
    assert record.entity_id == new_entity.id
    assert record.soul_crystal == "Acumen"
    assert record.rarity == "Lightning"
    assert record.enchant_level == 3
    assert old_entity in affected
    assert new_entity.id in affected
