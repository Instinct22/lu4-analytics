#!/usr/bin/env python3
"""Seed market scan records with diverse weapon variants (SA, rarity, enchant)."""
from __future__ import annotations

import argparse
import random
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import delete, select

from calculations.price_stats import recalculate_item_statistics
from database import SessionLocal
from models.item_encyclopedia import ItemEncyclopedia
from models.market import ImportLog, MarketRecord
from models.wiki import WikiEntity
from schemas.market_scan import ScanRecord, ScanPrice
from services.name_matching import clean_display_name
from seed_market_scan import (
    ACTIONS,
    CURRENCIES,
    build_seller_names,
    random_price,
)

SOURCE = "weapon_variants_seed"
GRADE_BASE_PRICE = {
    "": Decimal("50_000"),
    "NG": Decimal("20_000"),
    "D": Decimal("150_000"),
    "C": Decimal("500_000"),
    "B": Decimal("2_000_000"),
    "A": Decimal("8_000_000"),
    "S": Decimal("25_000_000"),
}
ENCHANT_LEVELS = tuple(range(1, 17))
RARITY_GRADES = frozenset({"B", "A", "S"})


@dataclass
class WeaponTemplate:
    base_name: str
    grade: str
    soul_crystals: list[str] = field(default_factory=list)
    rarities: list[tuple[str, str | None]] = field(default_factory=list)


def _api_style_name(name: str, rng: random.Random) -> str:
    """Game API often drops apostrophes in item names."""
    if rng.random() < 0.65:
        return name.replace("'", "")
    return name


def load_weapon_templates(db) -> list[WeaponTemplate]:
    rows = db.execute(
        select(WikiEntity, ItemEncyclopedia)
        .join(ItemEncyclopedia, WikiEntity.external_id == ItemEncyclopedia.external_id)
        .where(WikiEntity.entity_type == "item")
        .where(ItemEncyclopedia.section == "gear")
        .where(ItemEncyclopedia.type.like("Weapon%"))
    ).all()

    templates: list[WeaponTemplate] = []
    for entity, enc in rows:
        base_name = clean_display_name(entity.display_name or entity.name)
        if not base_name or "*" in base_name:
            continue
        modifiers = (enc.payload or {}).get("item_modifiers") or {}
        soul_crystals = [
            str(entry.get("name", "")).strip()
            for entry in (modifiers.get("soul_crystals") or [])
            if isinstance(entry, dict) and str(entry.get("name", "")).strip()
        ]
        rarities: list[tuple[str, str | None]] = []
        for entry in modifiers.get("rarity") or []:
            if not isinstance(entry, dict):
                continue
            rarity_name = str(entry.get("name", "")).strip()
            if not rarity_name:
                continue
            sa = str(entry.get("sa", "")).strip() or None
            rarities.append((rarity_name, sa))

        templates.append(
            WeaponTemplate(
                base_name=base_name,
                grade=(enc.grade or "").upper(),
                soul_crystals=soul_crystals,
                rarities=rarities,
            )
        )

    if not templates:
        raise RuntimeError(
            "No weapons found in wiki_entities/item_encyclopedia. "
            "Run scripts/import_wiki.py first."
        )
    return templates


def _pick_enchant(rng: random.Random) -> int | None:
    roll = rng.random()
    if roll < 0.45:
        return None
    if roll < 0.75:
        return rng.choice(ENCHANT_LEVELS[:6])
    if roll < 0.92:
        return rng.choice(ENCHANT_LEVELS[6:12])
    return rng.choice(ENCHANT_LEVELS[12:])


def build_variant_name(template: WeaponTemplate, rng: random.Random) -> str:
    base = _api_style_name(template.base_name, rng)
    soul = rng.choice(template.soul_crystals) if template.soul_crystals else None
    rarity_entry = rng.choice(template.rarities) if template.rarities else None
    rarity = rarity_entry[0] if rarity_entry else None
    rarity_sa = rarity_entry[1] if rarity_entry else None

    has_rarity = template.grade in RARITY_GRADES and template.rarities and rng.random() < 0.35
    has_sa = bool(template.soul_crystals) and rng.random() < 0.55
    enchant = _pick_enchant(rng)

    if has_rarity:
        if rarity_sa and rng.random() < 0.7:
            soul = rarity_sa
        body = f"{base} - {rarity}"
        if soul:
            body = f"{body} {soul}"
    elif has_sa and soul:
        body = f"{base} {soul}"
    else:
        body = base

    if enchant is not None:
        return f"+{enchant} {body}"
    return body


def weapon_base_price(template: WeaponTemplate, rng: random.Random) -> Decimal:
    base = GRADE_BASE_PRICE.get(template.grade, GRADE_BASE_PRICE[""])
    spread = Decimal(str(round(rng.uniform(0.85, 1.2), 4)))
    return max(Decimal("1000"), (base * spread).quantize(Decimal("1")))


def generate_records(
    total: int,
    templates: list[WeaponTemplate],
    sellers: list[str],
    days: int,
    rng: random.Random,
) -> list[ScanRecord]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    records: list[ScanRecord] = []

    for _ in range(total):
        template = rng.choice(templates)
        item_name = build_variant_name(template, rng)
        seller = rng.choice(sellers)
        action = rng.choice(ACTIONS)
        currency = rng.choice(CURRENCIES)
        base_price = weapon_base_price(template, rng)
        count = rng.randint(1, 5)
        offset_seconds = rng.randint(0, max(1, int(days * 24 * 3600)))
        timestamp = start + timedelta(seconds=offset_seconds)

        records.append(
            ScanRecord(
                action=action,
                name=seller,
                item=item_name,
                count=count,
                price=ScanPrice(
                    amount=random_price(base_price, rng, currency, action),
                    currency=currency,
                ),
                timestamp=timestamp,
            )
        )

    records.sort(key=lambda record: record.timestamp)
    return records


def clear_seed_data(db) -> tuple[int, int, list[uuid.UUID]]:
    entity_ids = db.scalars(
        select(MarketRecord.entity_id)
        .join(ImportLog, MarketRecord.import_log_id == ImportLog.id)
        .where(ImportLog.source == SOURCE)
        .where(MarketRecord.entity_id.is_not(None))
        .distinct()
    ).all()

    log_ids = db.scalars(select(ImportLog.id).where(ImportLog.source == SOURCE)).all()
    deleted_records = 0
    if log_ids:
        deleted_records = db.execute(
            delete(MarketRecord).where(MarketRecord.import_log_id.in_(log_ids))
        ).rowcount
    deleted_logs = db.execute(delete(ImportLog).where(ImportLog.source == SOURCE)).rowcount
    db.commit()
    return deleted_records, deleted_logs, entity_ids


def save_seed_batch(db, records: list[ScanRecord]) -> tuple[int, int, set]:
    log = ImportLog(source=SOURCE, status="success")
    db.add(log)
    db.flush()

    matched = 0
    affected_entities: set = set()
    from services.market_scan_service import save_scan_record

    for record in records:
        market_record, is_matched = save_scan_record(db, record, import_log_id=log.id)
        if is_matched and market_record.entity_id:
            matched += 1
            affected_entities.add(market_record.entity_id)

    log.records_count = len(records)
    log.matched_count = matched
    return len(records), matched, affected_entities


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--sellers", type=int, default=300)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--clear", action="store_true", help="Delete prior weapon variant seed records")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    db = SessionLocal()
    try:
        cleared_entities: list[uuid.UUID] = []
        if args.clear:
            deleted_records, deleted_logs, cleared_entities = clear_seed_data(db)
            print(f"Cleared {deleted_records} records and {deleted_logs} import logs")

        templates = load_weapon_templates(db)
        with_sa = sum(1 for t in templates if t.soul_crystals)
        with_rarity = sum(1 for t in templates if t.rarities)
        print(
            f"Loaded {len(templates)} weapons "
            f"({with_sa} with SA, {with_rarity} with rarity variants)"
        )

        sellers = build_seller_names(args.sellers, rng)
        records = generate_records(args.count, templates, sellers, args.days, rng)

        affected_entities: set[uuid.UUID] = set(cleared_entities)
        saved_total = 0
        matched_total = 0

        for offset in range(0, len(records), args.batch_size):
            batch = records[offset : offset + args.batch_size]
            saved_count, matched_count, batch_entities = save_seed_batch(db, batch)
            db.commit()
            saved_total += saved_count
            matched_total += matched_count
            affected_entities.update(batch_entities)
            print(
                f"Batch {offset // args.batch_size + 1}: "
                f"saved={saved_count}, matched={matched_count}, total={saved_total}"
            )

        print(f"Recalculating statistics for {len(affected_entities)} items...")
        for index, entity_id in enumerate(affected_entities, start=1):
            recalculate_item_statistics(db, entity_id)
            if index % 50 == 0:
                db.commit()
                print(f"  stats: {index}/{len(affected_entities)}")
        db.commit()

        sample_names = sorted({record.item for record in records})[:8]
        print("Sample variant names:")
        for name in sample_names:
            print(f"  - {name}")
        print(
            f"Done: {saved_total} records, {matched_total} matched, "
            f"{len(sellers)} sellers, source={SOURCE}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
