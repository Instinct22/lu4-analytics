"""Craft catalog and resources: normalization into tables and sliced endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from api.deps import get_current_user, hash_password
from models.craft import CraftItem, CraftMaterialSource, CraftRecipe, CraftRecipeMaterial
from models.user import User
from services.normalizers.craft import (
    CATALOG_META_KEY,
    RESOURCES_META_KEY,
    normalize_craft_catalog,
    normalize_craft_resources,
)
from tests.conftest import make_entity, scalars_by_model

CATALOG = {
    "generated_at": "2026-07-27T01:00:00+00:00",
    "product_count": 1,
    "variant_count": 1,
    "categories": {"weapon": {"D": [10]}},
    "sets": {"Bone Set": [10]},
    "items": {
        "10": {
            "id": 10,
            "name": "Bone Sword",
            "grade": "D",
            "type": "Sword",
            "category": "weapon",
            "set_name": "Bone Set",
            "npc_sell": 1000,
            "url": "/lu4/item/10",
            "description": "A sword",
            "stats": {"p_atk": 100},
        },
        "20": {"id": 20, "name": "Bone Fragment", "grade": "D", "url": "/lu4/item/20"},
        "30": {"id": 30, "name": "Stem", "grade": "NG", "url": "/lu4/item/30"},
    },
    "byProduct": {
        "10": [
            {
                "recipe_id": 99,
                "yield": 1,
                "rate": 100,
                "crafter_level": 20,
                "skill_level": "3",
                "mp": "50",
                "success": "100%",
                "recipe_url": "/lu4/item/99",
                "tree": [
                    {
                        "id": 20,
                        "amount": 2,
                        "children": [{"id": 30, "amount": 5, "children": []}],
                    }
                ],
            }
        ]
    },
}

RESOURCES = {
    "generated_at": "2026-07-27T01:00:00+00:00",
    "min_npc_level": 1,
    "max_npc_level": 80,
    "base_materials": [
        {
            "id": 30,
            "name": "Stem",
            "grade": "NG",
            "url": "/lu4/item/30",
            "desc": "plant",
            "spoil": [
                {
                    "npc_id": 500,
                    "npc_name": "Goblin",
                    "npc_url": "/lu4/npc/500",
                    "npc_level": "12",
                    "amount": "1",
                    "chance": "30%",
                    "chance_val": 30.0,
                    "locations": [{"name": "Gludio", "url": "/lu4/map/1"}],
                }
            ],
            "drop": [
                {
                    "npc_id": 501,
                    "npc_name": "Orc",
                    "npc_url": "/lu4/npc/501",
                    "npc_level": "unknown",
                    "amount": "2",
                    "chance": "5%",
                    "chance_val": 5.0,
                    "locations": [],
                }
            ],
        }
    ],
    "craft_materials_lte_30": [
        {
            "id": 20,
            "name": "Bone Fragment",
            "grade": "D",
            "url": "/lu4/item/20",
            "desc": "bone",
            "crafter_level": 20,
            "tree": [{"id": 30, "amount": 5, "children": []}],
            "spoil": [],
            "drop": [],
        }
    ],
}


class RecordingSession:
    """Collects added rows; delete/flush are no-ops for a full rewrite."""

    def __init__(self):
        self.added: list = []
        self.deleted_tables: list = []
        self._next_id = 1

    def execute(self, stmt):
        self.deleted_tables.append(stmt.table.name)
        return None

    def flush(self):
        # Recipes need their surrogate id before materials reference it.
        for row in self.added:
            if isinstance(row, CraftRecipe) and row.id is None:
                row.id = self._next_id
                self._next_id += 1

    def add(self, obj):
        self.added.append(obj)

    def scalar(self, _stmt):
        return None


def added_of(db, model):
    return [row for row in db.added if isinstance(row, model)]


def test_catalog_normalizer_fills_items_and_recipes():
    db = RecordingSession()
    normalize_craft_catalog(db, CATALOG)

    items = {row.external_id: row for row in added_of(db, CraftItem)}
    assert set(items) == {10, 20, 30}
    assert items[10].stats == {"p_atk": 100}
    assert items[10].description == "A sword"

    recipes = added_of(db, CraftRecipe)
    assert len(recipes) == 1
    assert recipes[0].product_external_id == 10
    assert recipes[0].recipe_external_id == 99
    assert recipes[0].variant_index == 0
    # The nested tree stays a blob for the client-side calculator.
    assert recipes[0].tree[0]["children"][0]["id"] == 30


def test_catalog_normalizer_flattens_nested_materials():
    db = RecordingSession()
    normalize_craft_catalog(db, CATALOG)

    materials = {row.material_external_id: row for row in added_of(db, CraftRecipeMaterial)}
    assert set(materials) == {20, 30}
    assert materials[20].is_direct is True
    assert materials[20].amount == 2
    # Nested material is recorded too, but not as a direct ingredient.
    assert materials[30].is_direct is False
    assert materials[30].amount == 5
    assert {m.recipe_id for m in materials.values()} == {1}


def test_catalog_normalizer_replaces_tables_and_stores_meta():
    db = RecordingSession()
    normalize_craft_catalog(db, CATALOG)

    assert set(db.deleted_tables) == {"craft_recipes", "craft_items"}
    meta = next(row for row in db.added if getattr(row, "dataset_key", None) == CATALOG_META_KEY)
    assert meta.payload["categories"] == {"weapon": {"D": [10]}}
    assert meta.payload["sets"] == {"Bone Set": [10]}
    assert meta.payload["variant_count"] == 1


def test_resources_normalizer_splits_sources_by_kind():
    db = RecordingSession()
    normalize_craft_resources(db, RESOURCES)

    sources = added_of(db, CraftMaterialSource)
    assert [(s.material_external_id, s.source_kind) for s in sources] == [
        (30, "spoil"),
        (30, "drop"),
    ]
    spoil, drop = sources
    assert spoil.npc_level == 12
    assert spoil.locations == [{"name": "Gludio", "url": "/lu4/map/1"}]
    # Unparsable levels keep the raw text and stay out of level filters.
    assert drop.npc_level is None
    assert drop.npc_level_raw == "unknown"


def test_resources_normalizer_meta_keeps_sections_and_counts():
    db = RecordingSession()
    normalize_craft_resources(db, RESOURCES)

    meta = next(row for row in db.added if getattr(row, "dataset_key", None) == RESOURCES_META_KEY)
    by_id = {m["id"]: m for m in meta.payload["materials"]}
    assert by_id[30]["section"] == "base"
    assert by_id[30]["spoil_count"] == 1
    assert by_id[30]["drop_count"] == 1
    assert by_id[20]["section"] == "craft"
    assert by_id[20]["tree"] == [{"id": 30, "amount": 5, "children": []}]
    # Spoil and drop arrays moved to the table and must not be duplicated here.
    assert "spoil" not in by_id[30]


def make_item(**kwargs):
    defaults = dict(
        external_id=10,
        name="Bone Sword",
        grade="D",
        type="Sword",
        category="weapon",
        set_name=None,
        npc_sell=1000,
        url="/lu4/item/10",
        is_recipe_scroll=False,
        description="A sword",
        stats=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_catalog_endpoint_lists_items_without_descriptions(client, mock_db):
    mock_db.scalars.side_effect = scalars_by_model({"CraftItem": [make_item()]})
    mock_db.scalar.side_effect = [
        SimpleNamespace(payload={"generated_at": "now", "categories": {}, "sets": {}, "variant_count": 1}),
        SimpleNamespace(
            payload={
                "materials": [
                    {"id": 1872, "spoil_count": 51, "drop_count": 344},
                    {"id": 9999, "spoil_count": 0, "drop_count": 0},
                ]
            }
        ),
    ]

    r = client.get("/api/craft/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["items"]["10"]["name"] == "Bone Sword"
    assert "description" not in body["items"]["10"]
    assert body["craftableIds"] == []
    assert body["farmMaterialIds"] == [1872]


def test_item_endpoint_includes_description(client, mock_db):
    item = make_item()

    def get_by_model(model, _id):
        if model is CraftItem:
            return item
        return None

    mock_db.get.side_effect = get_by_model
    r = client.get("/api/craft/items/10")
    assert r.status_code == 200
    assert r.json()["description"] == "A sword"


def test_item_endpoint_404(client, mock_db):
    mock_db.get.return_value = None
    assert client.get("/api/craft/items/999").status_code == 404


def test_material_sources_endpoint_groups_by_kind(craft_client, mock_db):
    rows = [
        SimpleNamespace(
            source_kind="spoil",
            npc_external_id=500,
            npc_name="Goblin",
            npc_url="/lu4/npc/500",
            npc_level=12,
            npc_level_raw="Lv. 12",
            amount="1",
            chance_text="30%",
            chance_val=30.0,
            locations=[{"name": "Gludio", "url": "/lu4/map/1"}],
        ),
        SimpleNamespace(
            source_kind="drop",
            npc_external_id=501,
            npc_name="Orc",
            npc_url="/lu4/npc/501",
            npc_level=None,
            npc_level_raw="unknown",
            amount="2",
            chance_text="5%",
            chance_val=5.0,
            locations=[],
        ),
    ]
    mock_db.scalars.side_effect = scalars_by_model({"CraftMaterialSource": rows})

    r = craft_client.get("/api/craft/resources/30/sources")
    assert r.status_code == 200
    body = r.json()
    assert [s["npc_id"] for s in body["spoil"]] == [500]
    assert body["drop"] == []
    assert body["spoil"][0]["npc_level"] == "12"
    assert body["spoil"][0]["locations"] == [{"name": "Gludio", "url": "/lu4/map/1"}]


def test_npc_materials_endpoint_is_not_shadowed_by_material_route(client, mock_db):
    mock_db.scalars.side_effect = scalars_by_model({"CraftMaterialSource": []})
    r = client.get("/api/craft/resources/npc/500")
    assert r.status_code == 200
    body = r.json()
    assert body["npc_id"] == 500
    assert body["npc_name"] == ""
    assert body["spoils"] == []
    assert body["drops"] == []


def test_npc_materials_fills_name_from_wiki_when_no_craft_sources(client, mock_db):
    entity = make_entity(
        entity_type="npc",
        external_id=25383,
        entity_key="npc:25383",
        name="Lu4 Wiki: NPC Revenant of Sir Calibus",
        display_name="Revenant of Sir Calibus",
        url="/lu4/npc/25383-revenant-of-sir-calibus",
        content_md="Revenant of Sir Calibus\nRaid Boss\nUndead, Lv. 34\n",
    )
    mock_db.scalars.side_effect = scalars_by_model(
        {
            "CraftMaterialSource": [],
            "WikiEntity": [entity],
            "EntityLink": [],
        }
    )

    r = client.get("/api/craft/resources/npc/25383")
    assert r.status_code == 200
    body = r.json()
    assert body["npc_id"] == 25383
    assert body["npc_name"] == "Revenant of Sir Calibus"
    assert body["npc_level"] == "34"
    assert body["npc_url"] == "/lu4/npc/25383-revenant-of-sir-calibus"
    assert body["spoils"] == []
    assert body["drops"] == []


def test_npc_materials_endpoint_names_materials(client, mock_db):
    source = SimpleNamespace(
        source_kind="spoil",
        material_external_id=30,
        npc_external_id=500,
        npc_name="Goblin",
        npc_url="/lu4/npc/500",
        npc_level=12,
        npc_level_raw="Lv. 12",
        amount="1",
        chance_text="30%",
        chance_val=30.0,
        locations=[{"name": "Gludio", "url": "/lu4/map/1"}],
    )
    mock_db.scalars.side_effect = scalars_by_model(
        {
            "CraftMaterialSource": [source],
            "CraftItem": [make_item(external_id=30, name="Stem", grade="NG")],
        }
    )

    r = client.get("/api/craft/resources/npc/500")
    assert r.status_code == 200
    body = r.json()
    assert body["npc_name"] == "Goblin"
    assert body["npc_level"] == "12"
    assert body["locations"] == [{"name": "Gludio", "url": "/lu4/map/1"}]
    assert body["spoils"][0]["materialName"] == "Stem"
    assert body["drops"] == []


def test_profitability_requires_nav_permission(client, mock_db, test_user):
    test_user.role = "driver"
    assert client.get("/api/craft/profitability").status_code == 403


def test_profitability_split_from_craft_prices(client, mock_db, test_user):
    from main import app
    from models.permissions import RolePermission

    test_user.role = "driver"
    mock_db.scalars.side_effect = scalars_by_model(
        {
            "RolePermission": [
                RolePermission(role="driver", permission="feature.craft_prices", allowed=True),
                RolePermission(role="driver", permission="nav.craft_profitability", allowed=False),
            ],
        }
    )
    assert client.get("/api/craft/profitability").status_code == 403
    app.dependency_overrides[get_current_user] = lambda: test_user


def test_profitability_grade_filter(client, mock_db, test_user):
    from main import app

    plain_user = User(
        id=uuid.uuid4(),
        username="member",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: plain_user

    recipe = SimpleNamespace(id=1, product_external_id=100, variant_index=0, yield_amount=1)
    item_d = SimpleNamespace(
        external_id=100,
        name="D Sword",
        grade="D",
        category="weapons/sword",
        npc_sell=1000,
    )
    item_c = SimpleNamespace(
        external_id=200,
        name="C Sword",
        grade="C",
        category="weapons/sword",
        npc_sell=2000,
    )

    def execute_side(_stmt):
        return SimpleNamespace(all=lambda: [(recipe, item_d)])

    mock_db.execute.side_effect = execute_side
    mock_db.scalars.side_effect = lambda _stmt: SimpleNamespace(all=lambda: [])

    r = client.get("/api/craft/profitability", params={"grades": "D"})
    assert r.status_code == 200
    body = r.json()
    assert "recipes" in body
    assert body["period"] == "1d"

    app.dependency_overrides[get_current_user] = lambda: test_user


def test_batch_period_prices_avg_and_last():
    from calculations.trading_analytics import batch_period_prices
    from uuid import uuid4

    entity_id = uuid4()
    ext_id = 57
    entity = SimpleNamespace(id=entity_id, external_id=ext_id, entity_type="item")
    now = datetime.now(timezone.utc)
    records = [
        SimpleNamespace(entity_id=entity_id, price=100, side="sell", recorded_at=now - timedelta(hours=2)),
        SimpleNamespace(entity_id=entity_id, price=200, side="sell", recorded_at=now - timedelta(hours=1)),
    ]

    db = MagicMock()
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [entity]),
        SimpleNamespace(all=lambda: records),
    ]

    start = now - timedelta(hours=3)
    result = batch_period_prices(db, [ext_id], start, now)
    assert result[ext_id]["avg_price"] == 150.0
    assert result[ext_id]["last_price"] == 200.0


def test_batch_period_prices_excludes_outlier():
    from calculations.trading_analytics import batch_period_prices
    from uuid import uuid4

    entity_id = uuid4()
    ext_id = 57
    entity = SimpleNamespace(id=entity_id, external_id=ext_id, entity_type="item")
    now = datetime.now(timezone.utc)
    records = [
        SimpleNamespace(entity_id=entity_id, price=1000, side="sell", recorded_at=now - timedelta(hours=5)),
        SimpleNamespace(entity_id=entity_id, price=1100, side="sell", recorded_at=now - timedelta(hours=4)),
        SimpleNamespace(entity_id=entity_id, price=1050, side="sell", recorded_at=now - timedelta(hours=3)),
        SimpleNamespace(entity_id=entity_id, price=1020, side="sell", recorded_at=now - timedelta(hours=2)),
        SimpleNamespace(entity_id=entity_id, price=111111, side="sell", recorded_at=now - timedelta(hours=1)),
    ]

    db = MagicMock()
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [entity]),
        SimpleNamespace(all=lambda: records),
    ]

    start = now - timedelta(hours=6)
    result = batch_period_prices(db, [ext_id], start, now)
    assert result[ext_id]["avg_price"] == 1042.5
    assert result[ext_id]["last_price"] == 1020.0


def test_material_breakdown_full_partial_and_empty():
    from services.craft_service import _material_breakdown

    stem = SimpleNamespace(name="Stem")
    ore = SimpleNamespace(name="Iron Ore")
    craft_by_ext = {1864: stem, 1869: ore}
    prices = {
        1864: {"avg": 10.0},
        1869: {"avg": 25.0},
    }
    materials = [(1864, 2), (1869, 1)]

    full = _material_breakdown(materials, prices, craft_by_ext, "avg")
    assert full == [
        {
            "material_id": 1864,
            "material_name": "Stem",
            "amount": 2,
            "unit_price": 10.0,
            "line_total": 20.0,
        },
        {
            "material_id": 1869,
            "material_name": "Iron Ore",
            "amount": 1,
            "unit_price": 25.0,
            "line_total": 25.0,
        },
    ]

    partial_prices = {
        1864: {"avg": 10.0},
        1869: {"avg": None},
    }
    partial = _material_breakdown(materials, partial_prices, craft_by_ext, "avg")
    assert partial[0]["line_total"] == 20.0
    assert partial[1]["unit_price"] is None
    assert partial[1]["line_total"] is None

    assert _material_breakdown([], prices, craft_by_ext, "avg") == []


def test_margin_npc_buy_ingredients_calculation():
    def margin_npc_buy_ingredients(
        revenue_npc_buy: float | None, cost_avg: float
    ) -> float | None:
        if revenue_npc_buy is None or cost_avg == 0:
            return None
        return revenue_npc_buy - cost_avg

    assert margin_npc_buy_ingredients(1000, 700) == 300
    assert margin_npc_buy_ingredients(500, 800) == -300
    assert margin_npc_buy_ingredients(None, 700) is None
    assert margin_npc_buy_ingredients(1000, 0) is None
    assert margin_npc_buy_ingredients(1000, 400) == 600


def test_resources_require_nav_permission(client, mock_db, test_user):
    test_user.role = "driver"
    assert client.get("/api/craft/resources").status_code == 403
