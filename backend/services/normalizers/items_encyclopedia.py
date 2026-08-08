"""Explode items_encyclopedia.json into item_encyclopedia + craft tables."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import settings
from models.craft import CraftItem, CraftMaterialSource, CraftRecipe, CraftRecipeMaterial
from models.item_encyclopedia import ItemEncyclopedia
from models.wiki import WikiEntity
from services.dataset_import import register_normalizer, upsert_blob
from services.encyclopedia_lib import sanitize_item_payload
from services.import_service import rematch_market_records
from services.name_matching import clean_display_name, normalize_product_name
from services.normalizers.craft import CATALOG_META_KEY, _npc_level
from calculations.price_stats import recalculate_item_statistics
from calculations.npc_prices import compute_npc_buy

ENCYCLOPEDIA_META_KEY = "items_encyclopedia_meta"
_NPC_LEVEL_RE = re.compile(r"Lv\.\s*(\d+)", re.IGNORECASE)


def _clean_wiki_path(url: str | None) -> str:
    """Keep path only: wiki sometimes stores ?dropPage= / ?spoilPage= on NPC urls."""
    if not url:
        return ""
    return str(url).strip().split("?", 1)[0]


def _locations_from_npc_html(raw_html_rel: str | None) -> list[dict[str, str]]:
    """Parse .item_title_location links from the NPC's raw wiki HTML."""
    if not raw_html_rel:
        return []
    path = Path(settings.wiki_path) / str(raw_html_rel).replace("\\", "/")
    if not path.is_file():
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    except OSError:
        return []
    block = soup.select_one(".item_title_location")
    if block is None:
        return []
    parent = block.parent or block
    locations: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in parent.find_all("a"):
        href = _clean_wiki_path(link.get("href"))
        name = " ".join((link.get_text() or "").split()).strip()
        if not name or "/lu4/location/" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        locations.append({"name": name, "url": href})
    return locations


@lru_cache(maxsize=1)
def _npc_wiki_index() -> dict[int, dict[str, Any]]:
    """NPC id → {url, locations, raw_html} from local masterwork wiki JSON."""
    root = Path(settings.wiki_path) / "library" / "data" / "npc"
    if not root.is_dir():
        return {}
    index: dict[int, dict[str, Any]] = {}
    for path in root.glob("*.json"):
        if "__" in path.name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        npc_id = data.get("id")
        if not isinstance(npc_id, int):
            continue
        locations: list[dict[str, str]] = []
        seen: set[str] = set()
        for link in data.get("links") or []:
            if not isinstance(link, dict) or link.get("type") != "location":
                continue
            name = str(link.get("name") or "").strip()
            url = _clean_wiki_path(link.get("url"))
            if not name:
                continue
            key = url or name
            if key in seen:
                continue
            seen.add(key)
            locations.append({"name": name, "url": url})
        index[npc_id] = {
            "url": _clean_wiki_path(data.get("url")),
            "name": clean_display_name(str(data.get("name") or "")),
            "locations": locations,
            "raw_html": data.get("raw_html"),
        }
    return index


def _level_from_wiki_text(text: str | None) -> str:
    if not text:
        return ""
    match = _NPC_LEVEL_RE.search(text)
    return match.group(1) if match else ""


def _identity_from_npc_html(raw_html_rel: str | None) -> dict[str, str]:
    """Parse NPC display name + level from raw wiki HTML title block."""
    if not raw_html_rel:
        return {}
    path = Path(settings.wiki_path) / str(raw_html_rel).replace("\\", "/")
    if not path.is_file():
        return {}
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {}
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    except OSError:
        return {}
    out: dict[str, str] = {}
    title = soup.select_one(".item_title .item-name__content")
    if title is not None:
        # Drop badges like "Raid Boss" that sit in .item-name__additional.
        for extra in title.select(".item-name__additional"):
            extra.decompose()
        name = " ".join((title.get_text() or "").split()).strip()
        if name:
            out["name"] = name
    type_line = soup.select_one(".item_title .item-name__type")
    if type_line is not None:
        level = _level_from_wiki_text(type_line.get_text() or "")
        if level:
            out["level"] = level
    return out


def resolve_npc_wiki_meta(npc_id: int, *, parse_html: bool = False) -> dict[str, Any]:
    """Url + locations (+ optional name/level) for one NPC.

    HTML is opt-in: bulk source lists use JSON only; a single NPC detail may
    parse the page when the JSON has no location links / identity fields.
    """
    file_meta = _npc_wiki_index().get(npc_id) or {}
    locations = list(file_meta.get("locations") or [])
    name = str(file_meta.get("name") or "")
    level = ""
    if parse_html and file_meta.get("raw_html"):
        if not locations:
            locations = _locations_from_npc_html(file_meta.get("raw_html"))
        identity = _identity_from_npc_html(file_meta.get("raw_html"))
        if not name and identity.get("name"):
            name = identity["name"]
        if identity.get("level"):
            level = identity["level"]
    return {
        "url": file_meta.get("url") or "",
        "locations": locations,
        "name": name,
        "level": level,
    }


def _source_npc_url(source: dict[str, Any], wiki: dict[str, Any] | None) -> str:
    raw = source.get("npc_url")
    if isinstance(raw, str) and raw.strip():
        return _clean_wiki_path(raw)
    if wiki and wiki.get("url"):
        return str(wiki["url"])
    return ""


def _source_locations(source: dict[str, Any], wiki: dict[str, Any] | None) -> list:
    raw = source.get("locations")
    if isinstance(raw, list) and raw:
        return raw
    if wiki and wiki.get("locations"):
        return list(wiki["locations"])
    return []


def _flatten_tree(nodes: list, depth: int = 0) -> Iterator[tuple[int, int, bool]]:
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        material_id = node.get("id")
        if isinstance(material_id, int):
            yield material_id, int(node.get("amount") or 1), depth == 0
        yield from _flatten_tree(node.get("children") or [], depth + 1)


def _import_craft_from_encyclopedia(db: Session, payload: dict[str, Any]) -> None:
    craft = payload.get("craft") or {}
    by_product = craft.get("by_product") or craft.get("byProduct") or {}
    items = payload.get("items") or {}

    referenced: set[int] = set()
    for raw_pid, variants in by_product.items():
        try:
            referenced.add(int(raw_pid))
        except (TypeError, ValueError):
            continue
        for variant in variants or []:
            if not isinstance(variant, dict):
                continue
            rid = variant.get("recipe_id")
            if isinstance(rid, int):
                referenced.add(rid)
            for mid, _, _ in _flatten_tree(variant.get("tree") or []):
                referenced.add(mid)

    db.execute(delete(CraftRecipe))
    db.execute(delete(CraftItem))
    db.flush()

    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        if iid not in referenced and item.get("section") != "gear":
            continue
        if iid not in referenced and not (item.get("craft") or {}).get("craftable"):
            continue
        if iid not in referenced:
            continue
        clean = sanitize_item_payload(item)
        npc_buy = clean.get("npc_buy")
        if npc_buy is None:
            npc_buy = compute_npc_buy(
                clean.get("npc_sell"),
                clean.get("grade") or "",
                clean.get("category") or "",
            )
        db.add(
            CraftItem(
                external_id=iid,
                name=clean.get("name") or f"#{iid}",
                grade=clean.get("grade") or "",
                type=clean.get("type") or "",
                category=clean.get("category") or "",
                set_name=clean.get("set_name"),
                npc_sell=clean.get("npc_sell"),
                npc_buy=npc_buy,
                url="",
                is_recipe_scroll=bool(clean.get("is_recipe_scroll")),
                description=clean.get("description") or clean.get("effects"),
                stats=clean.get("stats"),
            )
        )
    db.flush()

    for raw_pid, variants in by_product.items():
        try:
            product_id = int(raw_pid)
        except (TypeError, ValueError):
            continue
        for index, variant in enumerate(variants or []):
            if not isinstance(variant, dict):
                continue
            recipe = CraftRecipe(
                product_external_id=product_id,
                recipe_external_id=variant.get("recipe_id"),
                variant_index=index,
                yield_amount=int(variant.get("yield") or 1),
                rate=variant.get("rate"),
                crafter_level=variant.get("crafter_level"),
                skill_level=variant.get("skill_level"),
                mp=variant.get("mp"),
                success=variant.get("success"),
                recipe_url=None,
                tree=variant.get("tree") or [],
            )
            db.add(recipe)
            db.flush()
            for material_id, amount, is_direct in _flatten_tree(variant.get("tree") or []):
                db.add(
                    CraftRecipeMaterial(
                        recipe_id=recipe.id,
                        material_external_id=material_id,
                        amount=amount,
                        is_direct=is_direct,
                    )
                )

    item_icons = {
        str(raw_id): item["icon"]
        for raw_id, item in items.items()
        if isinstance(item, dict) and item.get("icon")
    }
    upsert_blob(
        db,
        CATALOG_META_KEY,
        {
            "generated_at": payload.get("generated_at"),
            "product_count": len(by_product),
            "variant_count": sum(len(v or []) for v in by_product.values()),
            "categories": craft.get("categories") or {},
            "sets": craft.get("sets") or {},
            "setMeta": _clean_set_meta(craft.get("set_meta") or craft.get("setMeta") or {}),
            "itemIcons": item_icons,
        },
        None,
    )


def _clean_set_meta(meta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, entry in meta.items():
        if not isinstance(entry, dict):
            out[key] = entry
            continue
        cleaned = {k: v for k, v in entry.items() if k != "url"}
        out[key] = cleaned
    return out


def _chance_val(source: dict[str, Any]) -> Decimal:
    raw = source.get("chance_val")
    if raw is not None:
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError):
            pass
    chance = str(source.get("chance") or "").replace("%", "").strip()
    if chance:
        try:
            return Decimal(chance)
        except (InvalidOperation, ValueError):
            pass
    return Decimal(0)


def _is_craft_material(item: dict[str, Any]) -> bool:
    """True only for farmable/craft materials (Coal, Asofe, …) — never gear or recipes."""
    if item.get("other_subcategory") == "materials":
        return True
    category = str(item.get("category") or "")
    if category.startswith("materials"):
        return True
    item_type = str(item.get("type") or "")
    return "Material" in item_type and item.get("section") == "other"


def _material_section(item: dict[str, Any]) -> str:
    craft = item.get("craft") if isinstance(item.get("craft"), dict) else {}
    if craft.get("craftable"):
        return "craft"
    return "base"


def _material_tree(item: dict[str, Any]) -> list:
    craft = item.get("craft") if isinstance(item.get("craft"), dict) else {}
    for variant in craft.get("variants") or []:
        if isinstance(variant, dict) and variant.get("tree"):
            return variant["tree"]
    return []


def _walk_recipe_material_ids(nodes: list, counts: dict[int, int]) -> None:
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        material_id = node.get("id")
        if isinstance(material_id, int):
            counts[material_id] = counts.get(material_id, 0) + 1
        _walk_recipe_material_ids(node.get("children") or [], counts)


def _craft_ingredient_usage(payload: dict[str, Any]) -> dict[int, int]:
    """How often each item id appears as an ingredient across craft recipe trees."""
    counts: dict[int, int] = {}
    craft = payload.get("craft") or {}
    by_product = craft.get("by_product") or craft.get("byProduct") or {}
    for variants in by_product.values():
        for variant in variants or []:
            if isinstance(variant, dict):
                _walk_recipe_material_ids(variant.get("tree") or [], counts)
    for item in (payload.get("items") or {}).values():
        if not isinstance(item, dict):
            continue
        craft_info = item.get("craft") if isinstance(item.get("craft"), dict) else {}
        for variant in craft_info.get("variants") or []:
            if isinstance(variant, dict):
                _walk_recipe_material_ids(variant.get("tree") or [], counts)
    return counts


#: Gear parts (Broadsword Blade, Avadon Breastplate Part, …) appear in few recipes;
#: shared resources (Coal, Asofe, Steel, …) appear in many.
_MIN_CRAFT_USAGE = 5


def _level_raw(source: dict[str, Any]) -> str:
    """Store the level as a bare number: the wiki writes it as "Lv. 36"."""
    level = source.get("npc_level")
    if isinstance(level, int):
        return str(level)
    parsed = _npc_level(source.get("npc_level_raw"))
    if parsed is not None:
        return str(parsed)
    return str(source.get("npc_level_raw") or "")


def _usable_sources(rows: Any) -> list[dict]:
    """Drop rows the UI cannot render: no monster name or no level to filter on."""
    usable: list[dict] = []
    for source in rows or []:
        if not isinstance(source, dict):
            continue
        if not source.get("npc_name") or not source.get("npc_id"):
            continue
        if not _level_raw(source).isdigit():
            continue
        usable.append(source)
    return usable


def _import_material_sources_from_encyclopedia(db: Session, payload: dict[str, Any]) -> None:
    """Populate craft resource tables with shared craft materials only (no weapons/armor/parts)."""
    db.execute(delete(CraftMaterialSource))
    db.flush()

    usage = _craft_ingredient_usage(payload)
    materials_meta: list[dict] = []
    for raw_id, item in (payload.get("items") or {}).items():
        if not isinstance(item, dict) or not _is_craft_material(item):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        if usage.get(iid, 0) < _MIN_CRAFT_USAGE:
            continue
        drops = _usable_sources(item.get("drops"))
        spoils = _usable_sources(item.get("spoils"))
        if not drops and not spoils:
            continue

        section = _material_section(item)
        craft = item.get("craft") if isinstance(item.get("craft"), dict) else {}
        variant = next((v for v in (craft.get("variants") or []) if isinstance(v, dict)), None)

        for kind, rows in (("spoil", spoils), ("drop", drops)):
            for order, source in enumerate(rows):
                npc_id = source.get("npc_id")
                wiki = resolve_npc_wiki_meta(npc_id) if isinstance(npc_id, int) else None
                db.add(
                    CraftMaterialSource(
                        material_external_id=iid,
                        source_kind=kind,
                        npc_external_id=npc_id,
                        npc_name=source.get("npc_name") or "",
                        npc_url=_source_npc_url(source, wiki),
                        npc_level=source.get("npc_level") if isinstance(source.get("npc_level"), int) else _npc_level(source.get("npc_level_raw")),
                        npc_level_raw=_level_raw(source),
                        amount=str(source.get("amount") or ""),
                        chance_text=str(source.get("chance") or "")[:32],
                        chance_val=_chance_val(source),
                        locations=_source_locations(source, wiki),
                        sort_order=order,
                    )
                )

        materials_meta.append(
            {
                "id": iid,
                "section": section,
                "name": item.get("name"),
                "grade": item.get("grade") or "NG",
                "url": item.get("url") or "",
                "desc": item.get("effects") or item.get("description") or "",
                "crafter_level": variant.get("crafter_level") if variant else None,
                "skill_level": variant.get("skill_level") if variant else None,
                "mp": variant.get("mp") if variant else None,
                "success": variant.get("success") if variant else None,
                "recipe_url": None,
                "tree": _material_tree(item),
                "spoil_count": len(spoils),
                "drop_count": len(drops),
            }
        )

    materials_meta.sort(key=lambda m: (m.get("name") or "").lower())

    upsert_blob(
        db,
        "craft_resources_meta",
        {
            "generated_at": payload.get("generated_at"),
            "materials": materials_meta,
        },
        None,
    )


def _sync_wiki_names_from_encyclopedia(db: Session) -> int:
    """Fix truncated wiki recipe titles from encyclopedia; refresh normalized keys."""
    enc_rows = db.scalars(select(ItemEncyclopedia)).all()
    if not enc_rows:
        return 0

    by_id = {item.external_id: item for item in enc_rows}
    entities = db.scalars(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.external_id.in_(list(by_id.keys())),
        )
    ).all()

    updated = 0
    for entity in entities:
        src = by_id[entity.external_id]
        wiki_display = (entity.display_name or "").strip()
        # Wiki catalog often stores recipe scrolls as bare "Recipe".
        if wiki_display.lower() in {"", "recipe"} and src.name:
            display = clean_display_name(src.name)
        else:
            display = wiki_display or clean_display_name(src.name)
        normalized = normalize_product_name(display)
        if entity.display_name == display and entity.name_normalized == normalized:
            continue
        entity.display_name = display
        entity.name_normalized = normalized
        updated += 1
    return updated


def _refresh_wiki_item_name_normalized(db: Session) -> int:
    """Recompute name_normalized for all wiki items after matching rules change."""
    entities = db.scalars(select(WikiEntity).where(WikiEntity.entity_type == "item")).all()
    updated = 0
    for entity in entities:
        normalized = normalize_product_name(entity.display_name or entity.name or "")
        if entity.name_normalized != normalized:
            entity.name_normalized = normalized
            updated += 1
    return updated


@register_normalizer("items_encyclopedia")
def normalize_items_encyclopedia(db: Session, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    db.execute(delete(ItemEncyclopedia))
    db.flush()

    for raw_id, item in (payload.get("items") or {}).items():
        if not isinstance(item, dict):
            continue
        external_id = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        clean = sanitize_item_payload(item)
        db.add(
            ItemEncyclopedia(
                external_id=external_id,
                section=clean.get("section") or "other",
                name=clean.get("name") or f"#{external_id}",
                grade=clean.get("grade") or "",
                type=clean.get("type") or "",
                other_subcategory=clean.get("other_subcategory"),
                icon=clean.get("icon"),
                url="",
                payload=clean,
            )
        )

    upsert_blob(
        db,
        ENCYCLOPEDIA_META_KEY,
        {
            "generated_at": payload.get("generated_at"),
            "item_count": payload.get("item_count"),
            "section_counts": payload.get("section_counts"),
            "library": payload.get("library"),
        },
        None,
    )

    _import_craft_from_encyclopedia(db, payload)
    _import_material_sources_from_encyclopedia(db, payload)
    _sync_wiki_names_from_encyclopedia(db)
    _refresh_wiki_item_name_normalized(db)
    _, affected = rematch_market_records(db)
    db.flush()
    for entity_id in affected:
        recalculate_item_statistics(db, entity_id)
