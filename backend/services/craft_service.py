"""Reads over the normalized craft tables."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Numeric, cast, func, or_, select
from sqlalchemy.orm import Session

from models.analytics import AnalyticsDataset, ItemStatistics
from models.craft import CraftItem, CraftMaterialSource, CraftRecipe, CraftRecipeMaterial
from models.item_encyclopedia import ItemEncyclopedia
from models.wiki import EntityLink, WikiEntity
from services.encyclopedia_lib import sanitize_item_payload
from services.market_service import prices_by_ids
from services.normalizers.craft import CATALOG_META_KEY, RESOURCES_META_KEY
from services.normalizers.items_encyclopedia import _level_from_wiki_text, resolve_npc_wiki_meta

#: NPC shop buy estimate: SellPrice × 2 × 1.2
SHOP_MARKUP = 2.4

GRADE_CRYSTAL_IDS: dict[str, int] = {
    "D": 1458,
    "C": 1459,
    "B": 1460,
    "A": 1461,
    "S": 1462,
}

APPRAISAL_TYPES = frozenset({"weapon", "armor", "jewelry"})
APPRAISAL_GRADES = frozenset({"NG", "D", "C", "B", "A", "S"})


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


#: Market fallback for items nobody trades: NPC sell price times a markup.
MARKET_MARKUP = 1.5


def profitability(db: Session, limit: int = 100, min_margin: float | None = None) -> dict:
    """Craft margin per recipe, computed in SQL instead of in the browser.

    Material cost uses direct materials only: nested crafts are an option, not
    an obligation, and buying the direct ingredients is the baseline strategy.
    """
    market_price = func.coalesce(ItemStatistics.avg_price, ItemStatistics.last_price)
    item_price = func.coalesce(
        market_price,
        cast(CraftItem.npc_sell, Numeric(14, 2)) * MARKET_MARKUP,
    )

    price_of_item = (
        select(
            CraftItem.external_id.label("external_id"),
            item_price.label("price"),
        )
        .outerjoin(
            WikiEntity,
            (WikiEntity.entity_type == "item")
            & (WikiEntity.external_id == CraftItem.external_id),
        )
        .outerjoin(
            ItemStatistics,
            (ItemStatistics.entity_id == WikiEntity.id) & (ItemStatistics.period == "all"),
        )
        .subquery("item_price")
    )

    material_cost = (
        select(
            CraftRecipeMaterial.recipe_id.label("recipe_id"),
            func.sum(CraftRecipeMaterial.amount * price_of_item.c.price).label("cost"),
            func.count(price_of_item.c.price).label("priced"),
            func.count(CraftRecipeMaterial.id).label("total"),
        )
        .outerjoin(
            price_of_item,
            price_of_item.c.external_id == CraftRecipeMaterial.material_external_id,
        )
        .where(CraftRecipeMaterial.is_direct.is_(True))
        .group_by(CraftRecipeMaterial.recipe_id)
        .subquery("material_cost")
    )

    product_price = price_of_item.alias("product_price")

    query = (
        select(
            CraftRecipe.product_external_id,
            CraftItem.name,
            CraftItem.grade,
            CraftRecipe.variant_index,
            CraftRecipe.yield_amount,
            product_price.c.price,
            material_cost.c.cost,
            material_cost.c.priced,
            material_cost.c.total,
        )
        .join(CraftItem, CraftItem.external_id == CraftRecipe.product_external_id)
        .join(material_cost, material_cost.c.recipe_id == CraftRecipe.id)
        .outerjoin(product_price, product_price.c.external_id == CraftRecipe.product_external_id)
        .where(
            product_price.c.price.is_not(None),
            material_cost.c.cost.is_not(None),
            material_cost.c.priced == material_cost.c.total,
        )
    )

    revenue = product_price.c.price * CraftRecipe.yield_amount
    margin = revenue - material_cost.c.cost
    if min_margin is not None:
        query = query.where(margin >= min_margin)
    query = query.order_by(margin.desc()).limit(limit)

    rows = db.execute(query).all()
    result = []
    for product_id, name, grade, variant, yield_amount, price, cost, _priced, _total in rows:
        revenue_value = float(price) * yield_amount
        cost_value = float(cost)
        result.append(
            {
                "product_id": product_id,
                "product_name": name,
                "grade": grade,
                "variant_index": variant,
                "yield": yield_amount,
                "unit_price": float(price),
                "revenue": revenue_value,
                "material_cost": cost_value,
                "margin": revenue_value - cost_value,
                "margin_pct": (
                    round((revenue_value - cost_value) / cost_value * 100, 2)
                    if cost_value > 0
                    else None
                ),
            }
        )
    return {"recipes": result}


def _resolve_main_unit_price(row: dict | None) -> float | None:
    """Main craft pricing: market VWAP → recent → NPC shop estimate."""
    market = _resolve_market_unit_price(row)
    if market is not None:
        return market
    npc = row.get("npc_sell") if row else None
    if npc is not None and float(npc) > 0:
        return float(npc) * SHOP_MARKUP
    return None


def _resolve_market_unit_price(row: dict | None) -> float | None:
    """Trader market only — never fill with NPC shop price."""
    if not row:
        return None
    for key in ("day_vwap", "recent_vwap"):
        val = row.get(key)
        if val is not None and float(val) > 0:
            return float(val)
    return None


def _shop_price(npc_sell: int | float | None) -> float | None:
    if npc_sell is None:
        return None
    value = float(npc_sell)
    if value <= 0:
        return None
    return value * SHOP_MARKUP


def _crystal_amount(stats: dict | None) -> int | None:
    if not isinstance(stats, dict):
        return None
    raw = stats.get("crystals")
    if raw is None:
        return None
    try:
        amount = int(raw)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _collect_base_amounts(
    tree: list,
    crafts: float,
    recipes_by_product: dict[int, list],
    *,
    depth: int = 0,
) -> dict[int, float]:
    """Walk recipe tree; accumulate only non-craftable / leaf materials × qty.

    Baked ``children`` amounts are already scaled for the parent line (same as
    the frontend calculator). Separate recipe expansion uses per-1-item trees,
    so those are multiplied by how many intermediates are needed.
    """
    totals: dict[int, float] = defaultdict(float)
    if crafts <= 0:
        return totals
    for node in tree or []:
        if not isinstance(node, dict):
            continue
        mid = node.get("id")
        if not isinstance(mid, int):
            continue
        amount = float(node.get("amount") or 1)
        need = amount * crafts
        children = node.get("children") or []
        if children:
            # Keep product-level scale; child amounts are pre-scaled in the blob.
            for mat_id, qty in _collect_base_amounts(
                children, crafts, recipes_by_product, depth=depth + 1
            ).items():
                totals[mat_id] += qty
            continue
        variants = recipes_by_product.get(mid) if depth < 12 else None
        if variants:
            nested = variants[0].tree or []
            for mat_id, qty in _collect_base_amounts(
                nested, need, recipes_by_product, depth=depth + 1
            ).items():
                totals[mat_id] += qty
            continue
        totals[mid] += need
    return totals


def _type_filter(item_type: str):
    if item_type == "weapon":
        return or_(
            CraftItem.category.startswith("weapons/"),
            CraftItem.type.ilike("Weapon%"),
        )
    if item_type == "armor":
        return or_(
            CraftItem.category.startswith("armors/"),
            CraftItem.type.ilike("Armor%"),
        )
    # jewelry
    return or_(
        CraftItem.category == "other/jewelry",
        CraftItem.type.ilike("Accessory%"),
        CraftItem.type.ilike("%Jewelry%"),
    )


def appraisal(
    db: Session,
    *,
    grade: str,
    item_type: str,
    limit: int = 100,
) -> dict:
    """Most profitable craftable items for the grade/type filter."""
    grade_key = (grade or "").strip().upper()
    type_key = (item_type or "").strip().lower()
    if grade_key not in APPRAISAL_GRADES:
        grade_key = "C"
    if type_key not in APPRAISAL_TYPES:
        type_key = "weapon"

    product_ids = list(
        db.scalars(
            select(CraftRecipe.product_external_id)
            .join(CraftItem, CraftItem.external_id == CraftRecipe.product_external_id)
            .where(CraftItem.grade == grade_key)
            .where(_type_filter(type_key))
            .distinct()
        ).all()
    )
    if not product_ids:
        return {"grade": grade_key, "type": type_key, "items": []}

    products = db.scalars(select(CraftItem).where(CraftItem.external_id.in_(product_ids))).all()
    recipes = db.scalars(
        select(CraftRecipe)
        .where(CraftRecipe.product_external_id.in_(product_ids))
        .order_by(CraftRecipe.product_external_id, CraftRecipe.variant_index)
    ).all()
    recipes_by_product: dict[int, list[CraftRecipe]] = defaultdict(list)
    for recipe in recipes:
        recipes_by_product[recipe.product_external_id].append(recipe)

    # All craftable products (for nested expansion of intermediate crafts).
    all_recipes = db.scalars(
        select(CraftRecipe).order_by(CraftRecipe.product_external_id, CraftRecipe.variant_index)
    ).all()
    all_recipes_by_product: dict[int, list[CraftRecipe]] = defaultdict(list)
    for recipe in all_recipes:
        all_recipes_by_product[recipe.product_external_id].append(recipe)

    base_needs_by_key: dict[tuple[int, int], dict[int, float]] = {}
    price_ids: set[int] = set(product_ids)
    crystal_id = GRADE_CRYSTAL_IDS.get(grade_key)
    if crystal_id is not None:
        price_ids.add(crystal_id)

    for product in products:
        for recipe in recipes_by_product.get(product.external_id, []):
            bases = _collect_base_amounts(recipe.tree or [], 1.0, all_recipes_by_product)
            base_needs_by_key[(product.external_id, recipe.variant_index)] = bases
            price_ids.update(bases.keys())

    price_map = (
        prices_by_ids(db, ",".join(str(i) for i in sorted(price_ids)), "main")
        if price_ids
        else {}
    )

    crystal_unit = None
    if crystal_id is not None:
        crow = price_map.get(str(crystal_id))
        if crow and crow.get("day_vwap") is not None and float(crow["day_vwap"]) > 0:
            crystal_unit = float(crow["day_vwap"])

    def _margin(sell: float | None, craft_cost: float | None) -> tuple[float | None, float | None]:
        if sell is None or craft_cost is None:
            return None, None
        margin = sell - craft_cost
        pct = round(margin / craft_cost * 100, 2) if craft_cost > 0 else None
        return margin, pct

    items_out: list[dict] = []
    for product in products:
        variants = recipes_by_product.get(product.external_id, [])
        for recipe in variants:
            bases = base_needs_by_key.get((product.external_id, recipe.variant_index), {})
            craft_cost: float | None = 0.0
            for mid, qty in bases.items():
                unit = _resolve_main_unit_price(price_map.get(str(mid)))
                if unit is None:
                    craft_cost = None
                    break
                craft_cost += unit * qty

            market_unit = _resolve_market_unit_price(price_map.get(str(product.external_id)))
            yield_amount = int(recipe.yield_amount or 1)
            market_price = market_unit * yield_amount if market_unit is not None else None
            shop_price = _shop_price(product.npc_sell)

            crystals = _crystal_amount(product.stats)
            crystal_price = (
                crystals * crystal_unit
                if crystals is not None and crystal_unit is not None
                else None
            )

            margin_market, margin_market_pct = _margin(market_price, craft_cost)
            margin_shop, margin_shop_pct = _margin(shop_price, craft_cost)
            margin_crystal, margin_crystal_pct = _margin(crystal_price, craft_cost)

            items_out.append(
                {
                    "product_id": product.external_id,
                    "product_name": product.name,
                    "grade": product.grade,
                    "type": product.type,
                    "category": product.category,
                    "variant_index": recipe.variant_index,
                    "rate": float(recipe.rate) if recipe.rate is not None else None,
                    "yield": yield_amount,
                    "craft_cost": craft_cost,
                    "market_price": market_price,
                    "shop_price": shop_price,
                    "crystal_amount": crystals,
                    "crystal_price": crystal_price,
                    "margin_market": margin_market,
                    "margin_market_pct": margin_market_pct,
                    "margin_shop": margin_shop,
                    "margin_shop_pct": margin_shop_pct,
                    "margin_crystal": margin_crystal,
                    "margin_crystal_pct": margin_crystal_pct,
                    # Keep legacy key for sorting / older clients (= craft→market).
                    "margin": margin_market,
                    "margin_pct": margin_market_pct,
                }
            )

    items_out.sort(
        key=lambda r: (
            0 if r.get("margin_market") is not None else 1,
            -(r["margin_market"] if r.get("margin_market") is not None else 0),
            r["product_name"],
            r["variant_index"],
        )
    )
    return {
        "grade": grade_key,
        "type": type_key,
        "items": items_out[: max(1, min(limit, 500))],
    }
