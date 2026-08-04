import re
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from calculations.price_stats import recalculate_item_statistics
from models.craft import CraftItem
from models.item_encyclopedia import ItemEncyclopedia
from models.market import ImportLog, MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.import_ import ImportRequest, ImportResponse
from services.name_matching import is_recipe_name, normalize_product_name, slugify


def get_or_create_seller(db: Session, name: str) -> Seller:
    slug = slugify(name)
    seller = db.scalar(select(Seller).where(Seller.slug == slug))
    if seller:
        return seller
    seller = Seller(name=name, slug=slug)
    db.add(seller)
    db.flush()
    return seller


def _wiki_item_by_external_id(db: Session, external_id: int) -> WikiEntity | None:
    return db.scalar(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.external_id == external_id,
        )
    )


def _escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sql_name_key(column):
    """Lowercase name with apostrophes removed — mirrors normalize_product_name keys."""
    return func.lower(func.regexp_replace(column, r"[''`ʼʹ]", "", "g"))


def _catalog_search_needle(normalized: str) -> str:
    """Build a short ILIKE needle that still finds apostrophe variants."""
    recipe = normalized.startswith("recipe:")
    core = normalized[7:].strip() if recipe else normalized
    # Prefer a long alphanumeric token (works for Butcher's ↔ Butchers).
    tokens = re_findall_tokens(core)
    if tokens:
        return max(tokens, key=len)
    return core


def re_findall_tokens(value: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", value.lower()) if len(t) >= 4]


def _external_id_from_catalog(db: Session, normalized: str) -> int | None:
    """Resolve item id via craft_items / item_encyclopedia (correct recipe names)."""
    if not normalized:
        return None

    recipe = normalized.startswith("recipe:")
    core = normalized[7:].strip() if recipe else normalized
    if len(core) < 2:
        return None

    needle = _escape_ilike(_catalog_search_needle(normalized))
    if len(needle) < 3:
        return None

    name_key_craft = _sql_name_key(CraftItem.name)
    craft_q = select(CraftItem).where(name_key_craft.like(f"%{needle}%", escape="\\"))
    if recipe:
        craft_q = craft_q.where(CraftItem.is_recipe_scroll.is_(True))
    else:
        craft_q = craft_q.where(CraftItem.is_recipe_scroll.is_(False))

    for item in db.scalars(craft_q.limit(120)).all():
        if normalize_product_name(item.name) == normalized:
            return item.external_id

    name_key_enc = _sql_name_key(ItemEncyclopedia.name)
    enc_q = select(ItemEncyclopedia).where(name_key_enc.like(f"%{needle}%", escape="\\"))
    if recipe:
        enc_q = enc_q.where(ItemEncyclopedia.name.ilike("Recipe:%"))
    else:
        enc_q = enc_q.where(~ItemEncyclopedia.name.ilike("Recipe:%"))

    for item in db.scalars(enc_q.limit(120)).all():
        if normalize_product_name(item.name) == normalized:
            return item.external_id

    return None


def find_item_by_name(db: Session, product_name: str) -> WikiEntity | None:
    normalized = normalize_product_name(product_name)
    if not normalized:
        return None

    entity = db.scalar(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.name_normalized == normalized,
        )
    )
    if entity:
        return entity

    external_id = _external_id_from_catalog(db, normalized)
    if external_id is not None:
        entity = _wiki_item_by_external_id(db, external_id)
        if entity:
            return entity

    recipe_query = is_recipe_name(product_name)
    entities = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(func.similarity(WikiEntity.name_normalized, normalized) > 0.85)
        .order_by(func.similarity(WikiEntity.name_normalized, normalized).desc())
        .limit(5)
    ).all()
    for candidate in entities:
        if is_recipe_name(candidate.display_name or candidate.name) != recipe_query:
            continue
        cand_norm = candidate.name_normalized or ""
        # Re-normalize display in case DB keys are stale after algorithm changes.
        if normalize_product_name(candidate.display_name or candidate.name) == normalized:
            return candidate
        if cand_norm.startswith("recipe:") != normalized.startswith("recipe:"):
            continue
        return candidate
    return None


def rematch_market_records(db: Session) -> tuple[int, set]:
    """Re-bind market rows after name-matching rules change.

    Touches recipe scrolls and previously unmatched rows.
    Returns (updated_count, affected_entity_ids).
    """
    rows = db.scalars(
        select(MarketRecord).where(
            or_(
                MarketRecord.product_name_raw.ilike("Recipe:%"),
                MarketRecord.entity_id.is_(None),
            )
        )
    ).all()
    updated = 0
    affected: set = set()
    for record in rows:
        entity = find_item_by_name(db, record.product_name_raw)
        new_norm = normalize_product_name(record.product_name_raw)
        changed = False
        if record.product_name_normalized != new_norm:
            record.product_name_normalized = new_norm
            changed = True
        new_entity_id = entity.id if entity else None
        if record.entity_id != new_entity_id:
            old_id = record.entity_id
            record.entity_id = new_entity_id
            if old_id:
                affected.add(old_id)
            if new_entity_id:
                affected.add(new_entity_id)
            changed = True
        if changed:
            updated += 1
    return updated, affected


# Backwards-compatible alias used by encyclopedia normalizer / tests.
def rematch_recipe_market_records(db: Session) -> tuple[int, set]:
    return rematch_market_records(db)


def import_price_records(db: Session, body: ImportRequest) -> ImportResponse:
    log = ImportLog(source=body.source, status="success")
    db.add(log)
    db.flush()

    matched = 0
    affected_entities: set = set()

    for record in body.records:
        seller = get_or_create_seller(db, record.seller)
        entity = find_item_by_name(db, record.product_name)
        normalized = normalize_product_name(record.product_name)
        if entity:
            matched += 1
            affected_entities.add(entity.id)

        db.add(
            MarketRecord(
                entity_id=entity.id if entity else None,
                product_name_raw=record.product_name,
                product_name_normalized=normalized,
                seller_id=seller.id,
                price=record.price,
                currency=record.currency,
                quantity=record.quantity,
                in_stock=record.in_stock,
                url=record.url,
                recorded_at=record.recorded_at or datetime.now(timezone.utc),
                import_log_id=log.id,
                raw_payload=record.model_dump(mode="json"),
            )
        )

    log.records_count = len(body.records)
    log.matched_count = matched
    db.commit()

    for entity_id in affected_entities:
        recalculate_item_statistics(db, entity_id)
    db.commit()

    return ImportResponse(
        import_id=log.id,
        records_count=len(body.records),
        matched_count=matched,
        unmatched_count=len(body.records) - matched,
    )


def list_import_logs(db: Session, limit: int = 50) -> list[ImportLog]:
    return list(
        db.scalars(select(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit)).all()
    )
