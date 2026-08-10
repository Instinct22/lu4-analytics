from decimal import Decimal
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.analytics import ItemStatistics
from models.market import ImportLog, MarketRecord
from models.wiki import WikiEntity
from calculations.price_outliers import partition_market_records


PERIODS = {
    "all": None,
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


def recalculate_item_statistics(db: Session, entity_id) -> None:
    now = datetime.now(timezone.utc)
    for period_key, delta in PERIODS.items():
        query = select(MarketRecord).where(MarketRecord.entity_id == entity_id)
        if delta:
            query = query.where(MarketRecord.recorded_at >= now - delta)

        records = db.scalars(query.order_by(MarketRecord.recorded_at)).all()
        stats = db.scalar(
            select(ItemStatistics).where(
                ItemStatistics.entity_id == entity_id,
                ItemStatistics.period == period_key,
            )
        )
        if stats is None:
            stats = ItemStatistics(entity_id=entity_id, period=period_key)
            db.add(stats)

        if not records:
            stats.min_price = None
            stats.max_price = None
            stats.avg_price = None
            stats.seller_count = 0
            stats.price_change_pct = None
            stats.last_price = None
            stats.computed_at = now
            continue

        clean_records, _ = partition_market_records(records)
        if not clean_records:
            clean_records = records
        clean_records = sorted(clean_records, key=lambda r: r.recorded_at)

        prices = [r.price for r in clean_records]
        stats.min_price = min(prices)
        stats.max_price = max(prices)
        stats.avg_price = sum(prices) / len(prices)
        stats.seller_count = len({r.seller_id for r in clean_records})
        stats.last_price = clean_records[-1].price
        if len(clean_records) >= 2 and clean_records[0].price and clean_records[0].price != 0:
            change = ((clean_records[-1].price - clean_records[0].price) / clean_records[0].price) * 100
            stats.price_change_pct = Decimal(str(round(max(-999_999.99, min(999_999.99, float(change))), 2)))
        else:
            stats.price_change_pct = None
        stats.computed_at = now


def get_dashboard_stats(db: Session) -> dict:
    entity_counts = dict(
        db.execute(
            select(WikiEntity.entity_type, func.count())
            .group_by(WikiEntity.entity_type)
            .order_by(WikiEntity.entity_type)
        ).all()
    )
    total_imports = db.scalar(select(func.count()).select_from(ImportLog)) or 0
    total_records = db.scalar(select(func.count()).select_from(MarketRecord)) or 0
    unmatched = db.scalar(
        select(func.count()).select_from(MarketRecord).where(MarketRecord.entity_id.is_(None))
    ) or 0
    recent_imports = db.scalars(
        select(ImportLog).order_by(ImportLog.created_at.desc()).limit(5)
    ).all()
    return {
        "entity_counts": entity_counts,
        "total_imports": total_imports,
        "total_market_records": total_records,
        "unmatched_records": unmatched,
        "recent_imports": recent_imports,
    }
