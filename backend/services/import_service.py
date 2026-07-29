from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from calculations.price_stats import recalculate_item_statistics
from models.market import ImportLog, MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.import_ import ImportRequest, ImportResponse
from services.name_matching import normalize_product_name, slugify


def get_or_create_seller(db: Session, name: str) -> Seller:
    slug = slugify(name)
    seller = db.scalar(select(Seller).where(Seller.slug == slug))
    if seller:
        return seller
    seller = Seller(name=name, slug=slug)
    db.add(seller)
    db.flush()
    return seller


def find_item_by_name(db: Session, product_name: str) -> WikiEntity | None:
    normalized = normalize_product_name(product_name)
    entity = db.scalar(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.name_normalized == normalized,
        )
    )
    if entity:
        return entity

    entities = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(func.similarity(WikiEntity.name_normalized, normalized) > 0.85)
        .order_by(func.similarity(WikiEntity.name_normalized, normalized).desc())
        .limit(1)
    ).all()
    return entities[0] if entities else None


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
