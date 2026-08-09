from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from calculations.npc_prices import compute_npc_buy
from calculations.trading_analytics import batch_period_prices, resolve_time_range
from models.analytics import AnalyticsDataset
from models.craft import CraftItem, CraftMaterialSource, CraftRecipe, CraftRecipeMaterial
from models.item_encyclopedia import ItemEncyclopedia
from models.wiki import EntityLink, WikiEntity
from services.encyclopedia_lib import sanitize_item_payload
from services.normalizers.craft import CATALOG_META_KEY, RESOURCES_META_KEY
from services.normalizers.items_encyclopedia import _level_from_wiki_text, resolve_npc_wiki_meta


def _meta(db: Session, key: str) -> dict:
    row = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == key))
    return row.payload if row and isinstance(row.payload, dict) else {}


def _item_json(item: CraftItem, *, with_text: bool, icon: str | None = None) -> dict:
    data = {
        "id": item.external_id,
        "name": item.name,
        "grade": item.grade,
        "type": item.type,
        "category": item.category,
        "set_name": item.set_name,
        "npc_sell": item.npc_sell,
        "npc_buy": item.npc_buy
        if item.npc_buy is not None
        else compute_npc_buy(item.npc_sell, item.grade, item.category),
        "url": item.url,
        "is_recipe_scroll": item.is_recipe_scroll,
        "stats": item.stats,
    }
    if icon:
        data["icon"] = icon
    if with_text:
        data["description"] = item.description
    return data


def _variant_json(recipe: CraftRecipe) -> dict:
    return {
        "recipe_id": recipe.recipe_external_id,
        "recipe_url": recipe.recipe_url,
        "rate": float(recipe.rate) if recipe.rate is not None else None,
        "crafter_level": recipe.crafter_level,
        "skill_level": recipe.skill_level,
        "mp": recipe.mp,
        "success": recipe.success,
        "yield": recipe.yield_amount,
        "tree": recipe.tree or [],
        "direct": [
            {"id": node.get("id"), "amount": node.get("amount")}
            for node in (recipe.tree or [])
            if isinstance(node, dict)
        ],
    }


def _farm_material_ids(db: Session) -> list[int]:
    meta = _meta(db, RESOURCES_META_KEY)
    ids: list[int] = []
    for material in meta.get("materials") or []:
        spoil = material.get("spoil_count") or 0
        drop = material.get("drop_count") or 0
        if spoil > 0 or drop > 0:
            mid = material.get("id")
            if mid is not None:
                ids.append(int(mid))
    return sorted(ids)


def catalog(db: Session) -> dict:
    """Light catalog for pickers: every item, no descriptions, no recipe trees."""
    items = db.scalars(select(CraftItem)).all()
    craftable_ids = db.scalars(select(CraftRecipe.product_external_id).distinct()).all()
    meta = _meta(db, CATALOG_META_KEY)
    item_icons = meta.get("itemIcons") or {}
    return {
        "generated_at": meta.get("generated_at"),
        "product_count": meta.get("product_count") or len(craftable_ids),
        "variant_count": meta.get("variant_count"),
        "items": {
            str(i.external_id): _item_json(
                i,
                with_text=False,
                icon=item_icons.get(str(i.external_id)),
            )
            for i in items
        },
        "categories": meta.get("categories") or {},
        "sets": meta.get("sets") or {},
        "setMeta": meta.get("setMeta") or {},
        "craftableIds": sorted(craftable_ids),
        "farmMaterialIds": _farm_material_ids(db),
    }


def item_detail(db: Session, item_id: int) -> dict | None:
    enc = db.get(ItemEncyclopedia, item_id)
    if enc is not None:
        payload = dict(enc.payload or {})
        payload.setdefault("id", enc.external_id)
        return sanitize_item_payload(payload)
    item = db.get(CraftItem, item_id)
    if item:
        return _item_json(item, with_text=True)
    return None


def recipe_closure(db: Session, product_id: int) -> dict:
    """Variants of a product plus of every craftable material it depends on.

    The client-side calculator walks nested materials, so one request has to
    carry the whole dependency closure — still kilobytes instead of megabytes.
    """
    pending = [product_id]
    visited: set[int] = set()
    by_product: dict[str, list[dict]] = {}
    involved: set[int] = {product_id}

    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)

        recipes = db.scalars(
            select(CraftRecipe)
            .where(CraftRecipe.product_external_id == current)
            .order_by(CraftRecipe.variant_index)
        ).all()
        if not recipes:
            continue
        by_product[str(current)] = [_variant_json(r) for r in recipes]

        material_ids = db.scalars(
            select(CraftRecipeMaterial.material_external_id)
            .distinct()
            .where(CraftRecipeMaterial.recipe_id.in_([r.id for r in recipes]))
        ).all()
        involved.update(material_ids)
        pending.extend(mid for mid in material_ids if mid not in visited)

    items = db.scalars(select(CraftItem).where(CraftItem.external_id.in_(involved))).all()
    return {
        "product_id": product_id,
        "byProduct": by_product,
        "items": {str(i.external_id): _item_json(i, with_text=True) for i in items},
    }


def material_usage(db: Session, material_id: int) -> list[dict]:
    """Products that consume the material, directly or through nested crafts."""
    rows = db.execute(
        select(
            CraftRecipe.product_external_id,
            CraftItem.name,
            func.bool_or(CraftRecipeMaterial.is_direct),
            func.sum(CraftRecipeMaterial.amount),
        )
        .join(CraftRecipe, CraftRecipe.id == CraftRecipeMaterial.recipe_id)
        .outerjoin(CraftItem, CraftItem.external_id == CraftRecipe.product_external_id)
        .where(CraftRecipeMaterial.material_external_id == material_id)
        .group_by(CraftRecipe.product_external_id, CraftItem.name)
        .order_by(CraftItem.name)
    ).all()
    return [
        {"product_id": pid, "product_name": name, "is_direct": direct, "amount": int(amount or 0)}
        for pid, name, direct, amount in rows
    ]


def resource_materials(db: Session) -> dict:
    meta = _meta(db, RESOURCES_META_KEY)
    counts = dict(
        db.execute(
            select(
                CraftMaterialSource.material_external_id,
                func.count(CraftMaterialSource.id),
            ).group_by(CraftMaterialSource.material_external_id)
        ).all()
    )
    levels = db.execute(
        select(func.min(CraftMaterialSource.npc_level), func.max(CraftMaterialSource.npc_level))
    ).one()
    return {
        "generated_at": meta.get("generated_at"),
        "min_npc_level": levels[0] if levels[0] is not None else meta.get("min_npc_level"),
        "max_npc_level": levels[1] if levels[1] is not None else meta.get("max_npc_level"),
        "materials": [
            {**material, "source_count": counts.get(material.get("id"), 0)}
            for material in meta.get("materials") or []
        ],
    }


def _level_text(row: CraftMaterialSource) -> str:
    """Plain number for the UI: the wiki stores levels as "Lv. 36"."""
    if row.npc_level is not None:
        return str(row.npc_level)
    return row.npc_level_raw or ""


def _npc_meta_lookup(db: Session, npc_ids: set[int], *, parse_html: bool = False) -> dict[int, dict]:
    """Fill missing npc_url / locations / name / level from wiki tables, then local wiki JSON."""
    if not npc_ids:
        return {}

    out: dict[int, dict] = {}
    entities = db.scalars(
        select(WikiEntity).where(
            WikiEntity.entity_type == "npc",
            WikiEntity.external_id.in_(npc_ids),
        )
    ).all()
    if entities:
        entity_ids = [e.id for e in entities]
        links = db.scalars(select(EntityLink).where(EntityLink.source_entity_id.in_(entity_ids))).all()
        target_ids = {link.target_entity_id for link in links}
        locations_by_id = {
            t.id: t
            for t in db.scalars(
                select(WikiEntity).where(
                    WikiEntity.id.in_(target_ids),
                    WikiEntity.entity_type == "location",
                )
            ).all()
        } if target_ids else {}
        locs_by_source: dict = {}
        for link in links:
            target = locations_by_id.get(link.target_entity_id)
            if target is None:
                continue
            locs_by_source.setdefault(link.source_entity_id, []).append(
                {"name": target.display_name or target.name, "url": target.url or ""}
            )
        for entity in entities:
            if entity.external_id is None:
                continue
            out[entity.external_id] = {
                "url": (entity.url or "").split("?", 1)[0],
                "locations": list(locs_by_source.get(entity.id) or []),
                "name": (entity.display_name or entity.name or "").strip(),
                "level": _level_from_wiki_text(entity.content_md),
            }

    # Local wiki JSON covers NPCs that are missing from wiki_entities or lack location links.
    for npc_id in npc_ids:
        file_meta = resolve_npc_wiki_meta(npc_id, parse_html=parse_html)
        current = out.get(npc_id) or {"url": "", "locations": [], "name": "", "level": ""}
        if not current.get("url") and file_meta.get("url"):
            current["url"] = file_meta["url"]
        if not current.get("locations") and file_meta.get("locations"):
            current["locations"] = list(file_meta["locations"])
        if not current.get("name") and file_meta.get("name"):
            current["name"] = file_meta["name"]
        if not current.get("level") and file_meta.get("level"):
            current["level"] = file_meta["level"]
        if current.get("url") or current.get("locations") or current.get("name") or current.get("level"):
            out[npc_id] = current
    return out


def _source_json(row: CraftMaterialSource, meta: dict | None = None) -> dict:
    meta = meta or {}
    npc_url = (row.npc_url or meta.get("url") or "").split("?", 1)[0]
    locations = row.locations or meta.get("locations") or []
    return {
        "npc_id": row.npc_external_id,
        "npc_name": row.npc_name,
        "npc_url": npc_url,
        "npc_level": _level_text(row),
        "amount": row.amount,
        "chance": row.chance_text,
        "chance_val": float(row.chance_val),
        "locations": locations,
    }


def material_sources(db: Session, material_id: int) -> dict:
    rows = db.scalars(
        select(CraftMaterialSource)
        .where(CraftMaterialSource.material_external_id == material_id)
        .order_by(CraftMaterialSource.sort_order)
    ).all()
    meta = _npc_meta_lookup(db, {r.npc_external_id for r in rows if r.npc_external_id is not None})
    return {
        "material_id": material_id,
        "spoil": [_source_json(r, meta.get(r.npc_external_id)) for r in rows if r.source_kind == "spoil"],
        "drop": [_source_json(r, meta.get(r.npc_external_id)) for r in rows if r.source_kind == "drop"],
    }


def npc_materials(db: Session, npc_id: int) -> dict:
    """Reverse lookup: which craft materials a single NPC yields."""
    rows = db.scalars(
        select(CraftMaterialSource)
        .where(CraftMaterialSource.npc_external_id == npc_id)
        .order_by(CraftMaterialSource.chance_val.desc())
    ).all()
    if not rows:
        meta = _npc_meta_lookup(db, {npc_id}, parse_html=True).get(npc_id) or {}
        return {
            "npc_id": npc_id,
            "npc_name": meta.get("name") or "",
            "npc_url": meta.get("url") or "",
            "npc_level": meta.get("level") or "",
            "locations": meta.get("locations") or [],
            "spoils": [],
            "drops": [],
        }

    names = {
        item.external_id: item
        for item in db.scalars(
            select(CraftItem).where(
                CraftItem.external_id.in_({r.material_external_id for r in rows})
            )
        ).all()
    }

    def entry(row: CraftMaterialSource) -> dict:
        item = names.get(row.material_external_id)
        return {
            "materialId": row.material_external_id,
            "materialName": item.name if item else f"#{row.material_external_id}",
            "materialGrade": item.grade if item else "",
            "materialUrl": item.url if item else "",
            "amount": row.amount,
            "chance": row.chance_text,
            "chance_val": float(row.chance_val),
        }

    meta = _npc_meta_lookup(db, {npc_id}, parse_html=True).get(npc_id) or {}
    locations: list = []
    for row in rows:
        for loc in row.locations or []:
            if loc not in locations:
                locations.append(loc)
    if not locations:
        locations = list(meta.get("locations") or [])

    head = rows[0]
    return {
        "npc_id": npc_id,
        "npc_name": head.npc_name or meta.get("name") or "",
        "npc_url": (head.npc_url or meta.get("url") or "").split("?", 1)[0],
        "npc_level": _level_text(head) or meta.get("level") or "",
        "locations": locations,
        "spoils": [entry(r) for r in rows if r.source_kind == "spoil"],
        "drops": [entry(r) for r in rows if r.source_kind == "drop"],
    }


#: Category prefixes for profitability filters (matches craft picker tabs).
CATEGORY_PREFIXES: dict[str, str] = {
    "weapons": "weapons/",
    "armors": "armors/",
    "jewelry": "other/jewelry",
    "materials": "materials/",
    "other": "other/",
}


def _matches_categories(category: str, categories: list[str] | None) -> bool:
    if not categories:
        return True
    for key in categories:
        prefix = CATEGORY_PREFIXES.get(key)
        if prefix and category.startswith(prefix):
            return True
    return False


def _product_kind(category: str) -> str:
    return "material" if category.startswith("materials/") else "item"


def _material_cost(
    materials: list[tuple[int, int]],
    prices: dict[int, dict[str, float | None]],
    basis: str,
) -> tuple[float, bool]:
    """Sum material prices; second value is True when any ingredient lacks a price."""
    total = 0.0
    incomplete = False
    for material_id, amount in materials:
        value = prices.get(material_id, {}).get(basis)
        if value is None:
            incomplete = True
            continue
        total += value * amount
    return total, incomplete


def _material_cost_strict(
    materials: list[tuple[int, int]],
    prices: dict[int, dict[str, float | None]],
    basis: str,
) -> float | None:
    total, incomplete = _material_cost(materials, prices, basis)
    if incomplete:
        return None
    return total


def _margin(revenue: float | None, cost: float | None) -> float | None:
    if revenue is None or cost is None:
        return None
    return revenue - cost


def profitability(
    db: Session,
    *,
    period: str = "1d",
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    grades: list[str] | None = None,
    categories: list[str] | None = None,
) -> dict:
    """Craft margin per recipe with period-based market prices and NPC sell."""
    start, end = resolve_time_range(period, from_date, to_date)

    query = select(CraftRecipe, CraftItem).join(
        CraftItem, CraftItem.external_id == CraftRecipe.product_external_id
    )
    if grades:
        query = query.where(CraftItem.grade.in_(grades))

    recipe_rows = db.execute(query).all()
    recipe_rows = [
        (recipe, item)
        for recipe, item in recipe_rows
        if _matches_categories(item.category, categories)
    ]
    if not recipe_rows:
        return {"period": period, "from": start.isoformat(), "to": end.isoformat(), "total": 0, "recipes": []}

    recipe_ids = [recipe.id for recipe, _ in recipe_rows]
    material_rows = db.scalars(
        select(CraftRecipeMaterial)
        .where(CraftRecipeMaterial.recipe_id.in_(recipe_ids))
        .where(CraftRecipeMaterial.is_direct.is_(True))
    ).all()
    materials_by_recipe: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for row in material_rows:
        materials_by_recipe[row.recipe_id].append((row.material_external_id, row.amount))

    external_ids: set[int] = set()
    for _recipe, item in recipe_rows:
        external_ids.add(item.external_id)
    for mats in materials_by_recipe.values():
        for material_id, _amount in mats:
            external_ids.add(material_id)

    period_prices = batch_period_prices(db, list(external_ids), start, end)
    craft_items = db.scalars(
        select(CraftItem).where(CraftItem.external_id.in_(external_ids))
    ).all()
    craft_by_ext = {item.external_id: item for item in craft_items}

    def _npc_buy_value(item: CraftItem | None) -> float | None:
        if item is None:
            return None
        value = item.npc_buy
        if value is None:
            value = compute_npc_buy(item.npc_sell, item.grade, item.category)
        return float(value) if value is not None else None

    def prices_for(ext_id: int) -> dict[str, float | None]:
        market = period_prices.get(ext_id, {})
        craft_item = craft_by_ext.get(ext_id)
        npc = craft_item.npc_sell if craft_item else None
        return {
            "avg": market.get("avg_price"),
            "last": market.get("last_price"),
            "npc": float(npc) if npc is not None else None,
            "npc_buy": _npc_buy_value(craft_item),
        }

    result = []
    for recipe, item in recipe_rows:
        mats = materials_by_recipe.get(recipe.id, [])
        product = prices_for(item.external_id)
        yield_amount = recipe.yield_amount

        revenue_avg = (
            product["avg"] * yield_amount if product["avg"] is not None else None
        )
        revenue_last = (
            product["last"] * yield_amount if product["last"] is not None else None
        )
        revenue_npc = (
            product["npc"] * yield_amount if product["npc"] is not None else None
        )
        revenue_npc_buy = (
            product["npc_buy"] * yield_amount if product["npc_buy"] is not None else None
        )

        mat_prices = {mid: prices_for(mid) for mid, _ in mats}
        if mats:
            cost_avg, cost_avg_incomplete = _material_cost(mats, mat_prices, "avg")
        else:
            cost_avg, cost_avg_incomplete = 0.0, False
        cost_last = _material_cost_strict(mats, mat_prices, "last") if mats else 0.0
        cost_npc = _material_cost_strict(mats, mat_prices, "npc") if mats else 0.0
        cost_npc_buy = _material_cost_strict(mats, mat_prices, "npc_buy") if mats else 0.0
        cost_avg_strict = None if cost_avg_incomplete else cost_avg

        result.append(
            {
                "product_id": item.external_id,
                "product_name": item.name,
                "grade": item.grade,
                "category": item.category,
                "kind": _product_kind(item.category),
                "variant_index": recipe.variant_index,
                "yield": yield_amount,
                "avg_price": product["avg"],
                "last_price": product["last"],
                "npc_sell": product["npc"],
                "npc_buy": product["npc_buy"],
                "revenue_avg": revenue_avg,
                "revenue_last": revenue_last,
                "revenue_npc": revenue_npc,
                "revenue_npc_buy": revenue_npc_buy,
                "material_cost_avg": cost_avg,
                "material_cost_avg_incomplete": cost_avg_incomplete,
                "material_cost_last": cost_last,
                "material_cost_npc": cost_npc,
                "material_cost_npc_buy": cost_npc_buy,
                "margin_avg": _margin(revenue_avg, cost_avg_strict),
                "margin_last": _margin(revenue_last, cost_last),
                "margin_npc": _margin(revenue_npc, cost_npc),
                "margin_npc_buy": _margin(revenue_npc_buy, cost_npc_buy),
            }
        )

    result.sort(
        key=lambda row: (
            row["margin_avg"] is None,
            -(row["margin_avg"] if row["margin_avg"] is not None else float("-inf")),
        )
    )
    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total": len(result),
        "recipes": result,
    }
