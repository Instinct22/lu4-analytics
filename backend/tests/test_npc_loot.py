"""NPC loot is served from npc_loot, with HTML parsing only as a fallback."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from services import wiki_service
from services.npc_loot_import import rows_for_npc
from tests.conftest import make_entity


def make_loot_row(**kwargs):
    defaults = dict(
        npc_external_id=5006,
        kind="drop",
        item_external_id=57,
        item_name="Adena",
        item_grade="",
        item_url="/lu4/item/57-adena",
        amount="1-10",
        chance_text="70.0%",
        chance_val=Decimal("70.0"),
        sort_order=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_rows_for_npc_keeps_kind_and_order():
    loot = {
        "spoils": [
            {
                "item_id": 1864,
                "item_name": "Stone of Purity",
                "item_grade": "",
                "item_url": "/lu4/item/1864",
                "amount": "1",
                "chance": "12.5%",
                "chance_val": 12.5,
            }
        ],
        "drops": [
            {
                "item_id": 57,
                "item_name": "Adena",
                "item_grade": "",
                "item_url": "/lu4/item/57",
                "amount": "1-10",
                "chance": "70.0%",
                "chance_val": 70.0,
            },
            {
                "item_id": 1060,
                "item_name": "Lesser Healing Potion",
                "item_grade": "NG",
                "item_url": "/lu4/item/1060",
                "amount": "1",
                "chance": "5.0%",
                "chance_val": 5.0,
            },
        ],
    }

    rows = rows_for_npc(5006, loot)

    assert [(r.kind, r.item_external_id, r.sort_order) for r in rows] == [
        ("spoil", 1864, 0),
        ("drop", 57, 0),
        ("drop", 1060, 1),
    ]
    assert all(r.npc_external_id == 5006 for r in rows)


def test_loot_response_reads_table(mock_db):
    mock_db.scalar.return_value = make_entity(entity_type="npc", external_id=5006)
    mock_db.scalars.return_value.all.return_value = [
        make_loot_row(),
        make_loot_row(kind="spoil", item_external_id=1864, item_name="Stone of Purity"),
    ]

    result = wiki_service.npc_loot_response(mock_db, 5006)

    assert [e["item_id"] for e in result["drops"]] == [57]
    assert [e["item_id"] for e in result["spoils"]] == [1864]
    assert result["drops"][0]["chance_val"] == 70.0


def test_loot_response_falls_back_to_html(mock_db, monkeypatch):
    entity = make_entity(entity_type="npc", external_id=5006, url="/lu4/npc/5006-goblin")
    mock_db.scalar.return_value = entity
    mock_db.scalars.return_value.all.return_value = []

    called: list[str] = []

    def fake_get_npc_loot(url: str) -> dict:
        called.append(url)
        return {"spoils": [], "drops": []}

    monkeypatch.setattr(wiki_service, "get_npc_loot", fake_get_npc_loot)
    result = wiki_service.npc_loot_response(mock_db, 5006)

    assert called == ["/lu4/npc/5006-goblin"]
    assert result == {"spoils": [], "drops": []}
