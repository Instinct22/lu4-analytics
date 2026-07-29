"""Item encyclopedia reads."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.analytics import AnalyticsDataset
from models.craft import CraftItem, CraftRecipe
from models.item_encyclopedia import ItemEncyclopedia
from services.encyclopedia_lib import sanitize_item_payload
from services.normalizers.craft import CATALOG_META_KEY
from services.normalizers.items_encyclopedia import ENCYCLOPEDIA_META_KEY

DUALS_DATASET_KEY = "duals_catalog"


def _meta(db: Session) -> dict:
    row = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == ENCYCLOPEDIA_META_KEY))
    return row.payload if row and isinstance(row.payload, dict) else {}


def _craft_meta(db: Session) -> dict:
    row = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == CATALOG_META_KEY))
    return row.payload if row and isinstance(row.payload, dict) else {}


def _light_item(row: ItemEncyclopedia) -> dict:
    payload = row.payload or {}
    stats = payload.get("stats") or {}
    return {
        "id": row.external_id,
        "name": row.name,
        "grade": row.grade,
        "type": row.type,
        "section": row.section,
        "other_subcategory": row.other_subcategory,
        "icon": row.icon,
        "slug": payload.get("slug"),
        "npc_sell": payload.get("npc_sell"),
        "category": payload.get("category"),
        "set_name": payload.get("set_name"),
        "stats": stats,
        "weight": stats.get("weight") or payload.get("weight"),
        "has_drop": bool(payload.get("has_drop") or payload.get("drops")),
        "has_spoil": bool(payload.get("has_spoil") or payload.get("spoils")),
        "craftable": bool((payload.get("craft") or {}).get("craftable")),
        "effects": payload.get("effects") or payload.get("description"),
    }


def _craft_item_json(item: CraftItem, *, icon: str | None = None) -> dict:
    data = {
        "id": item.external_id,
        "name": item.name,
        "grade": item.grade,
        "type": item.type,
        "category": item.category,
        "set_name": item.set_name,
        "npc_sell": item.npc_sell,
        "url": item.url,
        "is_recipe_scroll": item.is_recipe_scroll,
        "stats": item.stats,
    }
    if icon:
        data["icon"] = icon
    return data


def _collect_set_member_ids(sets: dict[str, Any], set_meta: dict[str, Any]) -> set[int]:
    needed: set[int] = set()
    for ids in sets.values():
        if isinstance(ids, list):
            for raw in ids:
                try:
                    needed.add(int(raw))
                except (TypeError, ValueError):
                    continue
    for entry in set_meta.values():
        if not isinstance(entry, dict):
            continue
        for key in ("allMemberIds", "craftableMemberIds"):
            for raw in entry.get(key) or []:
                try:
                    needed.add(int(raw))
                except (TypeError, ValueError):
                    continue
    return needed


def catalog(db: Session, *, section: str | None = None) -> dict:
    query = select(ItemEncyclopedia).order_by(ItemEncyclopedia.name)
    if section:
        query = query.where(ItemEncyclopedia.section == section)
    rows = db.scalars(query).all()
    meta = _meta(db)
    return {
        "generated_at": meta.get("generated_at"),
        "item_count": meta.get("item_count") or len(rows),
        "section_counts": meta.get("section_counts") or {},
        "items": [_light_item(r) for r in rows],
    }


def browse(db: Session) -> dict:
    """Single payload for the Items page: gear + sets slice + optional duals.

    Avoids shipping the full craft catalog (materials, recipe scrolls, etc.).
    """
    gear = catalog(db, section="gear")
    craft_meta = _craft_meta(db)
    sets = craft_meta.get("sets") or {}
    set_meta = craft_meta.get("setMeta") or {}
    item_icons = craft_meta.get("itemIcons") or {}

    needed_ids = _collect_set_member_ids(sets, set_meta)
    for entry in gear["items"]:
        needed_ids.add(int(entry["id"]))

    craft_items: dict[str, dict] = {}
    if needed_ids:
        rows = db.scalars(select(CraftItem).where(CraftItem.external_id.in_(needed_ids))).all()
        craft_items = {
            str(row.external_id): _craft_item_json(
                row,
                icon=item_icons.get(str(row.external_id)),
            )
            for row in rows
        }

    craftable_ids = sorted(db.scalars(select(CraftRecipe.product_external_id).distinct()).all())

    duals = None
    duals_row = db.scalar(
        select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == DUALS_DATASET_KEY)
    )
    if duals_row is not None and isinstance(duals_row.payload, dict):
        duals = {
            "generated_at": duals_row.generated_at.isoformat() if duals_row.generated_at else None,
            **duals_row.payload,
        }

    return {
        "generated_at": gear.get("generated_at") or craft_meta.get("generated_at"),
        "gear": gear,
        "craft": {
            "generated_at": craft_meta.get("generated_at"),
            "product_count": craft_meta.get("product_count") or len(craftable_ids),
            "variant_count": craft_meta.get("variant_count"),
            "items": craft_items,
            "categories": {},
            "sets": sets,
            "setMeta": set_meta,
            "craftableIds": craftable_ids,
            "byProduct": {},
        },
        "duals": duals,
    }


def item_detail(db: Session, external_id: int) -> dict | None:
    row = db.get(ItemEncyclopedia, external_id)
    if row is None:
        return None
    payload = dict(row.payload or {})
    payload.setdefault("id", row.external_id)
    payload.setdefault("section", row.section)
    out = sanitize_item_payload(payload)

    # Sources stay on /items/{id}/sources — detail payloads can be hundreds of KB.
    drops = out.get("drops") if isinstance(out.get("drops"), list) else []
    spoils = out.get("spoils") if isinstance(out.get("spoils"), list) else []
    out["has_drop"] = bool(out.get("has_drop") or drops)
    out["has_spoil"] = bool(out.get("has_spoil") or spoils)
    out.pop("drops", None)
    out.pop("spoils", None)

    craft = out.get("craft")
    if isinstance(craft, dict):
        out["craft"] = {"craftable": bool(craft.get("craftable")), "variants": []}

    return out


def item_sources(db: Session, external_id: int) -> dict | None:
    row = db.get(ItemEncyclopedia, external_id)
    if row is None:
        return None
    payload = sanitize_item_payload(row.payload or {})
    return {
        "id": row.external_id,
        "drops": payload.get("drops") or [],
        "spoils": payload.get("spoils") or [],
    }
