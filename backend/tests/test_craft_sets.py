"""Tests for craft catalog armor set parsing and grouping."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from craft_catalog.categories import apply_categories, build_sets  # noqa: E402
from craft_catalog.set_parse import parse_set_page  # noqa: E402
from craft_catalog.wiki_parse import load_html  # noqa: E402

SET_RAW = ROOT / "data" / "wiki" / "library" / "raw" / "lu4" / "set"
CATALOG_PATH = ROOT / "data" / "datasets" / "craft_catalog.json"


def test_parse_zubei_set_page_excludes_foundation():
    path = SET_RAW / "25-zubeis-breastplate.html"
    page = parse_set_page(load_html(path), "/lu4/set/25-zubeis-breastplate")
    assert page is not None
    assert page.is_pvp is False
    assert "Zubei" in page.name
    member_ids = [mid for mid, _ in page.members]
    assert 357 in member_ids
    assert 5710 in member_ids
    assert 11355 in page.foundation_ids
    assert 11355 not in member_ids
    assert len(member_ids) == 5


def test_parse_set_page_skips_pvp():
    matches = list(SET_RAW.glob("*dark-crystal-breastplate-pvp.html"))
    assert matches
    page = parse_set_page(load_html(matches[0]), f"/lu4/set/{matches[0].stem}")
    assert page is not None
    assert page.is_pvp is True


def test_build_sets_groups_sealed_a_grade():
    dark_crystal = SET_RAW / "524-dark-crystal-breastplate.html"
    page = parse_set_page(load_html(dark_crystal), "/lu4/set/524-dark-crystal-breastplate")
    assert page is not None

    craftable_ids = {5287, 5288, 5289, 5290, 5291, 5292}
    items = {
        str(i): {"id": i, "name": f"Sealed {name}", "grade": "A"}
        for i, name in [
            (5287, "Dark Crystal Breastplate"),
            (5288, "Dark Crystal Gaiters"),
            (5289, "Dark Crystal Helmet"),
            (5290, "Dark Crystal Gloves"),
            (5291, "Dark Crystal Boots"),
            (5292, "Dark Crystal Shield"),
        ]
    }
    sets_map = build_sets([page], craftable_ids, items)
    assert "Dark Crystal Breastplate" in sets_map
    members = sets_map["Dark Crystal Breastplate"]
    assert len(members) >= 4
    assert 5287 in members
    assert 5288 in members


def test_build_sets_merges_item_set_name_fallback():
    page = parse_set_page(
        load_html(SET_RAW / "25-zubeis-breastplate.html"),
        "/lu4/set/25-zubeis-breastplate",
    )
    craftable_ids = {357, 383, 503, 999}
    items = {
        "357": {"id": 357, "name": "Zubei's Breastplate", "grade": "B"},
        "383": {"id": 383, "name": "Zubei's Gaiters", "grade": "B"},
        "503": {"id": 503, "name": "Zubei's Helmet", "grade": "B"},
        "999": {"id": 999, "name": "Manticore Skin Boots", "grade": "C", "set_name": "Manticore Skin Boots"},
    }
    sets_map = build_sets([page], craftable_ids, items, fallback_by_item={999: "Manticore Skin Boots"})
    assert "Manticore Skin Boots" in sets_map
    assert sets_map["Manticore Skin Boots"] == [999]
    zubei_key = next(k for k in sets_map if "Zubei" in k)
    assert len(sets_map[zubei_key]) == 3


def test_build_sets_sealed_s_fallback_without_set_pages():
    craftable_ids = {6674, 6675, 6676, 6677, 6678, 6679}
    items = {
        str(i): {
            "id": i,
            "name": name,
            "grade": "S",
            "type": typ,
        }
        for i, name, typ in [
            (6674, "Sealed Imperial Crusader Breastplate", "Armor / Heavy / Upper Body"),
            (6675, "Sealed Imperial Crusader Gaiters", "Armor / Heavy / Lower Body"),
            (6676, "Sealed Imperial Crusader Gauntlets", "Armor / None / Gloves"),
            (6677, "Sealed Imperial Crusader Boots", "Armor / None / Boots"),
            (6678, "Sealed Imperial Crusader Shield", "Armor / None / Shield"),
            (6679, "Sealed Imperial Crusader Helmet", "Armor / None / Helmet"),
        ]
    }
    sets_map = build_sets([], craftable_ids, items)
    assert "Imperial Crusader Breastplate" in sets_map
    assert len(sets_map["Imperial Crusader Breastplate"]) == 6


def test_parse_dark_crystal_set_has_icon_and_effect():
    path = SET_RAW / "524-dark-crystal-breastplate.html"
    page = parse_set_page(load_html(path), "/lu4/set/524-dark-crystal-breastplate")
    assert page is not None
    assert page.set_id == 524
    assert page.slug == "dark-crystal-breastplate"
    assert page.icon == "armor_t74_u_i00.png"
    assert any("Cast. Spd." in line for line in page.effect_lines)
    assert 388 in [mid for mid, _ in page.members]


def test_build_set_meta_includes_all_and_craftable_members():
    from craft_catalog.set_meta import build_set_meta

    page = parse_set_page(
        load_html(SET_RAW / "25-zubeis-breastplate.html"),
        "/lu4/set/25-zubeis-breastplate",
    )
    craftable_ids = {357, 383, 503}
    items = {
        "357": {"id": 357, "name": "Zubei's Breastplate", "grade": "B"},
        "383": {"id": 383, "name": "Zubei's Gaiters", "grade": "B"},
        "503": {"id": 503, "name": "Zubei's Helmet", "grade": "B"},
    }
    sets_map = build_sets([page], craftable_ids, items)
    meta = build_set_meta([page], sets_map, items, craftable_ids)
    zubei_key = next(k for k in meta if "Zubei" in k)
    entry = meta[zubei_key]
    assert entry["craftableMemberIds"] == [357, 383, 503]
    assert 5710 in entry["allMemberIds"]
    assert entry["memberNames"]["5710"] == "Zubei's Gauntlets"
    assert entry.get("icon")


def test_build_set_meta_marks_leather_variant_non_canonical():
    from craft_catalog.set_meta import build_set_meta

    sets_map = {"Avadon Leather Mail": [999]}
    items = {"999": {"id": 999, "name": "Avadon Leather Mail", "grade": "B", "type": "Armor / Light / Full Body"}}
    meta = build_set_meta([], sets_map, items, {999})
    assert meta["Avadon Leather Mail"]["canonical"] is False


def test_enrich_set_meta_maps_a_grade_roster_to_sealed():
    from craft_catalog.set_meta import build_set_meta, enrich_set_meta

    page = parse_set_page(
        load_html(SET_RAW / "524-dark-crystal-breastplate.html"),
        "/lu4/set/524-dark-crystal-breastplate",
    )
    craftable_ids = {5287, 5288, 5289, 5290, 5291, 5292}
    items = {
        str(i): {"id": i, "name": name, "grade": "A", "url": f"/lu4/item/{i}-x", "icon": f"icon_{i}.png"}
        for i, name in [
            (5287, "Sealed Dark Crystal Breastplate"),
            (5288, "Sealed Dark Crystal Gaiters"),
            (5289, "Sealed Dark Crystal Helmet"),
            (5290, "Sealed Dark Crystal Gloves"),
            (5291, "Sealed Dark Crystal Boots"),
            (5292, "Sealed Dark Crystal Shield"),
        ]
    }
    sets_map = build_sets([page], craftable_ids, items)
    meta = build_set_meta([page], sets_map, items, craftable_ids)
    enrich_set_meta(meta, items, ROOT / "data" / "wiki" / "library", [page], craftable_ids)
    entry = meta["Dark Crystal Breastplate"]
    assert entry["allMemberIds"] == [5287, 5288, 5289, 5290, 5291, 5292]
    for pid in entry["allMemberIds"]:
        assert items[str(pid)]["name"].startswith("Sealed ")


def test_enrich_set_meta_fills_s_grade_icon_from_item_page():
    from craft_catalog.set_meta import build_set_meta, enrich_set_meta
    from craft_catalog.wiki_parse import parse_item_icon, load_html

    item_path = ROOT / "data" / "wiki" / "library" / "raw" / "lu4" / "item" / "6674-sealed-imperial-crusader-breastplate.html"
    if not item_path.is_file():
        return
    icon = parse_item_icon(load_html(item_path))
    assert icon == "armor_t88_u_i02.png"

    craftable_ids = {6674, 6675, 6676, 6677, 6678, 6679}
    items = {
        str(i): {"id": i, "name": name, "grade": "S", "type": typ}
        for i, name, typ in [
            (6674, "Sealed Imperial Crusader Breastplate", "Armor / Heavy / Upper Body"),
            (6675, "Sealed Imperial Crusader Gaiters", "Armor / Heavy / Lower Body"),
            (6676, "Sealed Imperial Crusader Gauntlets", "Armor / None / Gloves"),
            (6677, "Sealed Imperial Crusader Boots", "Armor / None / Boots"),
            (6678, "Sealed Imperial Crusader Shield", "Armor / None / Shield"),
            (6679, "Sealed Imperial Crusader Helmet", "Armor / None / Helmet"),
        ]
    }
    sets_map = build_sets([], craftable_ids, items)
    meta = build_set_meta([], sets_map, items, craftable_ids)
    wiki_root = ROOT / "data" / "wiki" / "library"
    enrich_set_meta(meta, items, wiki_root)
    entry = meta["Imperial Crusader Breastplate"]
    assert entry.get("icon") == "armor_t88_u_i02.png"
    assert entry.get("slug")
    assert entry.get("id") == 6674
    assert len(entry.get("memberNames") or {}) == 6


def test_build_sets_sealed_s_major_arcana_has_four_parts():
    craftable_ids = {6684, 6685, 6686, 6687}
    items = {
        str(i): {"id": i, "name": name, "grade": "S", "type": typ}
        for i, name, typ in [
            (6684, "Sealed Major Arcana Robe", "Armor / Robe / Upper Body"),
            (6685, "Sealed Major Arcana Gloves", "Armor / None / Gloves"),
            (6686, "Sealed Major Arcana Boots", "Armor / None / Boots"),
            (6687, "Sealed Major Arcana Circlet", "Armor / None / Helmet"),
        ]
    }
    sets_map = build_sets([], craftable_ids, items)
    assert "Major Arcana Robe" in sets_map
    assert sets_map["Major Arcana Robe"] == [6684, 6685, 6686, 6687]


def test_regression_catalog_has_set_meta():
    if not CATALOG_PATH.is_file():
        return
    import json

    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    set_meta = payload.get("setMeta") or {}
    assert len(set_meta) >= len(payload.get("sets") or {})
    dark = set_meta.get("Dark Crystal Breastplate")
    if dark:
        assert dark.get("icon")
        assert dark.get("effect") or dark.get("effectRaw")
        all_ids = dark.get("allMemberIds") or []
        craft = dark.get("craftableMemberIds") or []
        assert len(all_ids) >= len(craft)
        for pid in all_ids:
            item = payload.get("items", {}).get(str(pid)) or {}
            name = item.get("name") or (dark.get("memberNames") or {}).get(str(pid))
            assert name and name.startswith("Sealed "), f"expected sealed part, got {name} for {pid}"


def test_regression_catalog_has_a_and_s_sets():
    if not CATALOG_PATH.is_file():
        return
    import json

    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items = payload.get("items") or {}
    grade_counts: dict[str, int] = {}
    for member_ids in (payload.get("sets") or {}).values():
        first = items.get(str(member_ids[0]))
        grade = (first or {}).get("grade") or "NG"
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    assert grade_counts.get("A", 0) > 0
    assert grade_counts.get("S", 0) > 0

    avadon = payload.get("sets", {}).get("Avadon Breastplate")
    assert avadon is not None
    assert len(avadon) >= 4


def test_apply_categories_does_not_build_sets():
    payload = {
        "items": {
            "434": {
                "id": 434,
                "name": "White Tunic",
                "grade": "D",
                "type": "Armor / Robe / Upper Body",
                "set_name": "Some Set",
            }
        },
        "byProduct": {"434": [{"recipe_id": 999}]},
        "sets": {"Existing Set": [434]},
    }
    apply_categories(payload)
    assert payload["sets"] == {"Existing Set": [434]}
