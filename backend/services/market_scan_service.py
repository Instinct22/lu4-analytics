from sqlalchemy.orm import Session

from core.currency import normalize_currency
from models.market import ImportLog, MarketRecord
from schemas.market_scan import ScanRecord
from services.import_service import get_or_create_seller, resolve_market_item
from services.name_matching import normalize_product_name


def save_scan_record(
    db: Session,
    record: ScanRecord,
    *,
    import_log_id=None,
) -> tuple[MarketRecord, bool]:
    seller = get_or_create_seller(db, record.name)
    resolved = resolve_market_item(db, record.item)
    normalized = normalize_product_name(record.item)

    market_record = MarketRecord(
        entity_id=resolved.entity.id if resolved.entity else None,
        product_name_raw=record.item,
        product_name_normalized=normalized,
        soul_crystal=resolved.soul_crystal,
        rarity=resolved.rarity,
        armor_class=resolved.armor_class,
        sealed=resolved.sealed,
        enchant_level=resolved.enchant_level,
        seller_id=seller.id,
        price=record.price.amount,
        currency=normalize_currency(record.price.currency),
        side=record.action,
        quantity=record.count,
        recorded_at=record.timestamp,
        import_log_id=import_log_id,
        raw_payload=record.model_dump(mode="json"),
    )
    db.add(market_record)
    db.flush()
    return market_record, resolved.entity is not None


def save_scan_batch(db: Session, records: list[ScanRecord]) -> tuple[int, int, set]:
    log = ImportLog(source="game_scan", status="success")
    db.add(log)
    db.flush()

    matched = 0
    affected_entities: set = set()

    for record in records:
        market_record, is_matched = save_scan_record(db, record, import_log_id=log.id)
        if is_matched and market_record.entity_id:
            matched += 1
            affected_entities.add(market_record.entity_id)

    log.records_count = len(records)
    log.matched_count = matched
    return len(records), matched, affected_entities
