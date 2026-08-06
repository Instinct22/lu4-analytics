import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from calculations.price_stats import recalculate_item_statistics
from models.craft import CraftItem
from models.item_encyclopedia import ItemEncyclopedia
from models.market import ImportLog, MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.import_ import ImportRequest, ImportResponse
from services.name_matching import (
    is_recipe_name,
    normalize_product_name,
    slugify,
)
from services.variant_lexicon import classify_market_name


@dataclass(frozen=True)
class ResolvedMarketItem:
    entity: WikiEntity | None
    enchant_level: int | None
    soul_crystal: str | None
    rarity: str | None
    armor_class: str | None
    sealed: bool | None


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


def _pick_canonical_entity(db: Session, entities: list[WikiEntity]) -> WikiEntity | None:
    """Disambiguate several wiki items sharing one normalized name.

    Many weapon soul-ability variants (e.g. Conjurer's Knife Acumen/Focus/Haste)
    carry the same wiki title as the clean item, so they collapse to the same
    ``name_normalized``. Prefer the encyclopedia's visible base (section ``gear``)
    over ``excluded`` variants; break ties by the smallest external id.
    """
    if not entities:
        return None
    if len(entities) == 1:
        return entities[0]

    ext_ids = [e.external_id for e in entities if e.external_id is not None]
    sections: dict[int, str] = {}
    if ext_ids:
        rows = db.execute(
            select(ItemEncyclopedia.external_id, ItemEncyclopedia.section).where(
                ItemEncyclopedia.external_id.in_(ext_ids)
            )
        ).all()
        sections = {row.external_id: row.section for row in rows}

    def rank(entity: WikiEntity) -> tuple[int, int]:
        section = sections.get(entity.external_id) if entity.external_id is not None else None
        if section == "gear":
            tier = 0
        elif section and section != "excluded":
            tier = 1
        elif section is None:
            tier = 2
        else:  # excluded variant
            tier = 3
        return (tier, entity.external_id if entity.external_id is not None else 1 << 62)

    return min(entities, key=rank)


def _entity_by_normalized(db: Session, normalized: str) -> WikiEntity | None:
    if not normalized:
        return None
    entities = db.scalars(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.name_normalized == normalized,
        )
    ).all()
    return _pick_canonical_entity(db, list(entities))


def _encyclopedia_row(db: Session, entity: WikiEntity) -> ItemEncyclopedia | None:
    if entity.external_id is None:
        return None
    return db.get(ItemEncyclopedia, entity.external_id)


def _gear_kind(row: ItemEncyclopedia | None) -> str:
    if row is None:
        return "other"
    parts = [p.strip().lower() for p in (row.type or "").split("/") if p.strip()]
    if not parts:
        return "other"
    head = parts[0]
    if head == "weapon":
        return "weapon"
    if head == "armor":
        return "armor"
    if head == "accessory":
        return "accessory"
    return "other"


def _entity_supports_weapon_variant(
    db: Session,
    entity: WikiEntity,
    soul_crystal: str | None,
    rarity: str | None,
) -> bool:
    """Validate soul-ability against encyclopedia; dash-rarity is trusted."""
    if rarity is not None:
        return True
    if soul_crystal is None:
        return True
    row = _encyclopedia_row(db, entity)
    if row is None:
        return False
    modifiers = (row.payload or {}).get("item_modifiers") or {}
    rarity_entries = [e for e in (modifiers.get("rarity") or []) if isinstance(e, dict)]
    soul_entries = [e for e in (modifiers.get("soul_crystals") or []) if isinstance(e, dict)]
    sa_names = {str(e.get("name", "")).strip().lower() for e in soul_entries}
    sa_names |= {str(e.get("sa", "")).strip().lower() for e in rarity_entries if e.get("sa")}
    return soul_crystal.strip().lower() in sa_names


def _find_sealed_twin(db: Session, base_name: str) -> WikiEntity | None:
    """Prefer the Sealed catalog entry for an unsealed armor/jewelry base name."""
    if not base_name:
        return None
    sealed_norm = normalize_product_name(f"Sealed {base_name}")
    sealed = _entity_by_normalized(db, sealed_norm)
    if sealed is not None:
        return sealed
    # Catalog lookup when wiki name_normalized is stale.
    external_id = _external_id_from_catalog(db, sealed_norm)
    if external_id is not None:
        return _wiki_item_by_external_id(db, external_id)
    return None


def _prefer_gear_entity(db: Session, entity: WikiEntity | None) -> WikiEntity | None:
    """When several wiki rows share a name, prefer the encyclopedia gear base."""
    if entity is None:
        return None
    key = entity.name_normalized or normalize_product_name(
        entity.display_name or entity.name or ""
    )
    if not key:
        return entity
    preferred = _entity_by_normalized(db, key)
    return preferred or entity


def _fold_to_sealed_canonical(db: Session, entity: WikiEntity | None) -> WikiEntity | None:
    """Fold unsealed armor/jewelry onto the Sealed gear base when available."""
    if entity is None:
        return None
    row = _encyclopedia_row(db, entity)
    kind = _gear_kind(row)
    if kind not in {"armor", "accessory"}:
        return entity

    name = (entity.display_name or entity.name or "").strip()
    if name.lower().startswith("sealed "):
        # Duplicate Sealed rows exist (gear + excluded); always prefer gear.
        return _prefer_gear_entity(db, entity)

    if row and isinstance(row.payload, dict):
        group = row.payload.get("sealed_group")
        if isinstance(group, dict):
            sealed_id = group.get("sealed_id")
            if isinstance(sealed_id, int):
                sealed_entity = _wiki_item_by_external_id(db, sealed_id)
                if sealed_entity is not None:
                    # sealed_id on excluded twins may point at the excluded Sealed
                    # row — re-pick by name so charts bind to the gear canon.
                    return _prefer_gear_entity(db, sealed_entity)

    twin = _find_sealed_twin(db, name)
    return twin or entity


def _match_full_name(db: Session, product_name: str, normalized: str) -> WikiEntity | None:
    """Legacy match on the full name: exact -> catalog -> trigram similarity."""
    entity = _entity_by_normalized(db, normalized)
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
        # Prefer the canonical (gear) twin over excluded variants sharing a name.
        canonical = _entity_by_normalized(db, cand_norm) or candidate
        # Re-normalize display in case DB keys are stale after algorithm changes.
        if normalize_product_name(candidate.display_name or candidate.name) == normalized:
            return canonical
        if cand_norm.startswith("recipe:") != normalized.startswith("recipe:"):
            continue
        return canonical
    return None


def _is_sealed_family(entity: WikiEntity, row: ItemEncyclopedia | None) -> bool:
    """True when the canonical entity is (or belongs to) a Sealed gear entry."""
    name = (entity.display_name or entity.name or "").strip().lower()
    if name.startswith("sealed "):
        return True
    if row and isinstance(row.payload, dict):
        group = row.payload.get("sealed_group")
        if isinstance(group, dict) and group.get("sealed_id") is not None:
            return True
        if row.payload.get("unseal_variants"):
            return True
    return False


def resolve_market_item(db: Session, product_name: str) -> ResolvedMarketItem:
    """Resolve a raw market name to a canonical base entity + variant attrs.

    Weapons fold SA/rarity onto the clean gear base. Armor/jewelry fold onto the
    Sealed encyclopedia entry (when present) with armor_class / sealed flags.
    """
    parsed = classify_market_name(product_name)
    if not parsed.full_normalized:
        return ResolvedMarketItem(
            entity=None,
            enchant_level=parsed.enchant_level,
            soul_crystal=None,
            rarity=None,
            armor_class=None,
            sealed=None,
        )

    soul = parsed.soul_crystal
    rarity = parsed.rarity
    armor_class = parsed.armor_class

    entity: WikiEntity | None = None

    # Prefer Sealed catalog name, then stripped base, then Sealed twin of base
    # (covers armor class suffixes and unsealed jewelry like "Phoenix Ring").
    if parsed.sealed:
        entity = _entity_by_normalized(db, parsed.full_normalized)
        if entity is None:
            entity = _match_full_name(db, product_name, parsed.full_normalized)
    if entity is None and parsed.base_normalized:
        entity = _entity_by_normalized(db, parsed.base_normalized)
    if entity is None and parsed.base_name:
        entity = _find_sealed_twin(db, parsed.base_name)
    if entity is None:
        entity = _entity_by_normalized(db, parsed.full_normalized)
    if entity is None:
        entity = _match_full_name(db, product_name, parsed.full_normalized)

    if entity is not None:
        entity = _fold_to_sealed_canonical(db, entity)
        row = _encyclopedia_row(db, entity)
        kind = _gear_kind(row)

        if kind in {"armor", "accessory"}:
            sealed_attr: bool | None = None
            if _is_sealed_family(entity, row) or parsed.sealed or armor_class is not None:
                # Sealed family: prefix → True, unsealed/class piece → False.
                sealed_attr = True if parsed.sealed else False
            return ResolvedMarketItem(
                entity=entity,
                enchant_level=parsed.enchant_level,
                soul_crystal=None,
                rarity=None,
                armor_class=armor_class if kind == "armor" else None,
                sealed=sealed_attr,
            )

        # Weapon (or other): apply SA / rarity when validated against base.
        if (soul or rarity) and parsed.base_normalized:
            base = _entity_by_normalized(db, parsed.base_normalized) or entity
            if base is not None and _entity_supports_weapon_variant(db, base, soul, rarity):
                base_kind = _gear_kind(_encyclopedia_row(db, base))
                if base_kind in {"weapon", "other"}:
                    return ResolvedMarketItem(
                        entity=base,
                        enchant_level=parsed.enchant_level,
                        soul_crystal=soul,
                        rarity=rarity,
                        armor_class=None,
                        sealed=None,
                    )

        return ResolvedMarketItem(
            entity=entity,
            enchant_level=parsed.enchant_level,
            soul_crystal=None,
            rarity=None,
            armor_class=None,
            sealed=None,
        )

    # Unmatched — still return parsed structural attrs for debugging/admin.
    sealed_attr = True if parsed.sealed else (False if armor_class is not None else None)
    return ResolvedMarketItem(
        entity=None,
        enchant_level=parsed.enchant_level,
        soul_crystal=soul,
        rarity=rarity,
        armor_class=armor_class,
        sealed=sealed_attr,
    )


def find_item_by_name(db: Session, product_name: str) -> WikiEntity | None:
    return resolve_market_item(db, product_name).entity


def rematch_market_records(db: Session) -> tuple[int, set]:
    """Re-bind market rows after name-matching rules change.

    Recomputes the canonical entity plus variant attributes for every record.
    Returns (updated_count, affected_entity_ids).
    """
    rows = db.scalars(select(MarketRecord)).all()
    updated = 0
    affected: set = set()
    for record in rows:
        resolved = resolve_market_item(db, record.product_name_raw)
        new_norm = normalize_product_name(record.product_name_raw)
        changed = False
        if record.product_name_normalized != new_norm:
            record.product_name_normalized = new_norm
            changed = True
        new_entity_id = resolved.entity.id if resolved.entity else None
        if record.entity_id != new_entity_id:
            old_id = record.entity_id
            record.entity_id = new_entity_id
            if old_id:
                affected.add(old_id)
            if new_entity_id:
                affected.add(new_entity_id)
            changed = True
        if record.soul_crystal != resolved.soul_crystal:
            record.soul_crystal = resolved.soul_crystal
            changed = True
        if record.rarity != resolved.rarity:
            record.rarity = resolved.rarity
            changed = True
        if record.armor_class != resolved.armor_class:
            record.armor_class = resolved.armor_class
            changed = True
        if record.sealed != resolved.sealed:
            record.sealed = resolved.sealed
            changed = True
        if record.enchant_level != resolved.enchant_level:
            record.enchant_level = resolved.enchant_level
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
        resolved = resolve_market_item(db, record.product_name)
        normalized = normalize_product_name(record.product_name)
        if resolved.entity:
            matched += 1
            affected_entities.add(resolved.entity.id)

        db.add(
            MarketRecord(
                entity_id=resolved.entity.id if resolved.entity else None,
                product_name_raw=record.product_name,
                product_name_normalized=normalized,
                soul_crystal=resolved.soul_crystal,
                rarity=resolved.rarity,
                armor_class=resolved.armor_class,
                sealed=resolved.sealed,
                enchant_level=resolved.enchant_level,
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
