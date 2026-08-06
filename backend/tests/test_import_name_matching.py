"""Recipe scrolls must resolve to their own wiki entity, not the product."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from models.craft import CraftItem
from models.item_encyclopedia import ItemEncyclopedia
from services.import_service import find_item_by_name
from tests.conftest import make_entity, scalars_by_model


def test_find_item_by_name_keeps_recipe_distinct_via_craft():
    product = make_entity(
        id=uuid.uuid4(),
        entity_key="item:1463",
        external_id=1463,
        name="Soulshot (D-Grade)",
        display_name="Soulshot (D-Grade)",
        name_normalized="soulshot (d-grade)",
    )
    recipe = make_entity(
        id=uuid.uuid4(),
        entity_key="item:1804",
        external_id=1804,
        name="Recipe",
        display_name="Recipe",
        name_normalized="recipe",
    )
    craft_recipe = SimpleNamespace(
        external_id=1804,
        name="Recipe: Soulshot (D-Grade)",
        is_recipe_scroll=True,
    )

    db = MagicMock()
    # Exact WikiEntity miss (empty), craft candidate hit, wiki by external_id.
    db.scalar.return_value = recipe

    def scalars_handler(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        if entity is CraftItem:
            return SimpleNamespace(all=lambda: [craft_recipe])
        return SimpleNamespace(all=lambda: [])

    db.scalars.side_effect = scalars_handler

    found = find_item_by_name(db, "Recipe: Soulshot (D-Grade)")
    assert found is recipe
    assert found.external_id == 1804
    assert found.id != product.id


def test_find_item_by_name_matches_product_without_recipe_prefix():
    product = make_entity(
        id=uuid.uuid4(),
        entity_key="item:1463",
        external_id=1463,
        name="Soulshot (D-Grade)",
        display_name="Soulshot (D-Grade)",
        name_normalized="soulshot (d-grade)",
    )
    db = MagicMock()
    db.scalars.side_effect = scalars_by_model({"WikiEntity": [product]})

    found = find_item_by_name(db, "Soulshot (D-Grade)")
    assert found is product


def test_find_item_by_name_matches_apostrophe_via_encyclopedia():
    product = make_entity(
        id=uuid.uuid4(),
        entity_key="item:1510",
        external_id=1510,
        name="Butcher's Sword",
        display_name="Butcher's Sword",
        name_normalized="butchers sword",
    )
    enc = SimpleNamespace(external_id=1510, name="Butcher's Sword")

    db = MagicMock()
    db.scalar.return_value = product  # _wiki_item_by_external_id

    def scalars_handler(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        if entity is ItemEncyclopedia:
            return SimpleNamespace(all=lambda: [enc])
        return SimpleNamespace(all=lambda: [])

    db.scalars.side_effect = scalars_handler

    found = find_item_by_name(db, "Butchers Sword")
    assert found is product
    assert found.external_id == 1510
