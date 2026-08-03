#!/usr/bin/env python3
"""Generate synthetic market scan records as if a game bot collected trader data."""
from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, select

from calculations.price_stats import recalculate_item_statistics
from database import SessionLocal
from models.market import ImportLog, MarketRecord
from models.wiki import WikiEntity
from schemas.market_scan import ScanRecord, ScanPrice
from services import craft_service
from services.market_scan_service import save_scan_batch

EXTRA_NICK_PARTS = (
    "craft",
    "res",
    "mat",
    "bulk",
    "wh",
    "npc",
    "bot",
    "auto",
    "cash",
    "coin",
    "aden",
    "mc",
    "zerg",
    "clan",
    "pvp",
    "pve",
    "farm",
    "shop",
)


def clear_scan_data(db) -> tuple[int, int, list[uuid.UUID]]:
    entity_ids = db.scalars(
        select(MarketRecord.entity_id)
        .where(MarketRecord.side.is_not(None))
        .where(MarketRecord.entity_id.is_not(None))
        .distinct()
    ).all()

    deleted_records = db.execute(
        delete(MarketRecord).where(MarketRecord.side.is_not(None))
    ).rowcount
    deleted_logs = db.execute(
        delete(ImportLog).where(ImportLog.source == "game_scan")
    ).rowcount
    db.commit()
    return deleted_records, deleted_logs, entity_ids


MASTER_COIN_EXTERNAL_ID = 4037


def load_craft_resources(db, rng: random.Random) -> list[tuple[str, Decimal]]:
    payload = craft_service.resource_materials(db)
    materials = payload.get("materials") or []

    resource_ids: list[int] = []
    resource_names: dict[int, str] = {}
    for material in materials:
        mid = material.get("id")
        if mid is None:
            continue
        resource_ids.append(int(mid))
        resource_names[int(mid)] = str(material.get("name") or mid)

    # Always include Master Coin for craft-monitor seeding
    if MASTER_COIN_EXTERNAL_ID not in resource_ids:
        resource_ids.append(MASTER_COIN_EXTERNAL_ID)
        resource_names[MASTER_COIN_EXTERNAL_ID] = "Master Coin"

    entities = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id.in_(resource_ids))
    ).all()
    by_external_id = {entity.external_id: entity for entity in entities}

    items: list[tuple[str, Decimal]] = []
    for external_id in resource_ids:
        entity = by_external_id.get(external_id)
        name = entity.display_name if entity else resource_names[external_id]
        if external_id == MASTER_COIN_EXTERNAL_ID:
            items.append((name, Decimal(rng.randint(50, 400))))
        else:
            items.append((name, base_price_for_item(name, rng)))

    if not items:
        raise RuntimeError(
            "No craft resources found. Import craft datasets / wiki first "
            "(craft_resources_meta materials list is empty)."
        )
    return items

SELLER_PREFIXES = (
    "Dark",
    "Shadow",
    "Iron",
    "Gold",
    "Silver",
    "Crystal",
    "Storm",
    "Night",
    "Fire",
    "Ice",
    "Wild",
    "Royal",
    "Lucky",
    "Fast",
    "Pro",
)

SELLER_SUFFIXES = (
    "Trader",
    "Shop",
    "Market",
    "Dealer",
    "Store",
    "Boss",
    "King",
    "Lord",
    "Master",
    "Hunter",
    "Farmer",
    "Miner",
    "Smith",
    "Wolf",
    "Fox",
)

NICK_PARTS = (
    "sisi",
    "xX",
    "pro",
    "mega",
    "ultra",
    "neo",
    "dark",
    "lite",
    "top",
    "best",
    "farm",
    "trade",
    "sell",
    "buy",
    "l2",
    "lu4",
)

CURRENCIES = ("adena", "master coin")
ACTIONS = ("buy", "sell")


def build_seller_names(count: int, rng: random.Random) -> list[str]:
    nick_parts = NICK_PARTS + EXTRA_NICK_PARTS
    names: set[str] = set()
    while len(names) < count:
        style = rng.randint(0, 4)
        if style == 0:
            name = f"{rng.choice(SELLER_PREFIXES)}{rng.choice(SELLER_SUFFIXES)}{rng.randint(1, 9999)}"
        elif style == 1:
            name = f"{rng.choice(nick_parts)}{rng.randint(1, 999)}{rng.choice(nick_parts)}{rng.randint(1, 999)}"
        elif style == 2:
            name = f"{rng.choice(nick_parts)}{rng.randint(10, 99999)}"
        elif style == 3:
            name = f"{rng.choice(SELLER_PREFIXES)}{rng.choice(nick_parts)}{rng.randint(1, 9999)}"
        else:
            name = f"{rng.choice(nick_parts)}_{rng.choice(nick_parts)}{rng.randint(1, 9999)}"
        names.add(name)
    return list(names)


def base_price_for_item(name: str, rng: random.Random) -> Decimal:
    lower = name.lower()
    if "master coin" in lower:
        return Decimal(rng.randint(50, 400))
    if "ore" in lower or "nugget" in lower:
        return Decimal(rng.randint(80, 900))
    if "mold" in lower or "steel" in lower:
        return Decimal(rng.randint(3_000, 35_000))
    if "stone of purity" in lower or "varnish of purity" in lower:
        return Decimal(rng.randint(15_000, 120_000))
    if "bone" in lower or "powder" in lower:
        return Decimal(rng.randint(150, 2_500))
    if "thread" in lower or "cord" in lower or "braid" in lower or "hemp" in lower:
        return Decimal(rng.randint(200, 4_000))
    if "leather" in lower or "suede" in lower or "skin" in lower:
        return Decimal(rng.randint(300, 6_000))
    if "coal" in lower or "cokes" in lower or "charcoal" in lower:
        return Decimal(rng.randint(100, 1_800))
    if "varnish" in lower:
        return Decimal(rng.randint(500, 8_000))
    return Decimal(rng.randint(200, 10_000))


def random_price(base: Decimal, rng: random.Random, currency: str, action: str) -> Decimal:
    spread = rng.uniform(0.85, 1.25)
    if action == "buy":
        spread *= rng.uniform(0.9, 1.0)
    else:
        spread *= rng.uniform(1.0, 1.15)

    if currency == "master coin":
        coin_base = max(Decimal("1"), (base / Decimal("250000")).quantize(Decimal("1")))
        price = coin_base * Decimal(str(round(spread, 4)))
        return max(Decimal("1"), price.quantize(Decimal("0.01")))

    price = base * Decimal(str(round(spread, 4)))
    return max(Decimal("1"), price.quantize(Decimal("1")))


def generate_records(
    total: int,
    items: list[tuple[str, Decimal]],
    sellers: list[str],
    days: int,
    rng: random.Random,
) -> list[ScanRecord]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    records: list[ScanRecord] = []

    for _ in range(total):
        item_name, base_price = rng.choice(items)
        seller = rng.choice(sellers)
        action = rng.choice(ACTIONS)
        currency = rng.choice(CURRENCIES)
        count = rng.randint(50, 15_000)
        lower = item_name.lower()
        if "ore" in lower or "nugget" in lower or "coal" in lower:
            count = rng.randint(500, 25_000)
        elif "thread" in lower or "bone" in lower or "powder" in lower:
            count = rng.randint(100, 8_000)

        offset_seconds = rng.randint(0, int(days * 24 * 3600))
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--sellers", type=int, default=800)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clear", action="store_true", help="Delete existing game scan records first")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    db = SessionLocal()
    try:
        cleared_entities: list[uuid.UUID] = []
        if args.clear:
            deleted_records, deleted_logs, cleared_entities = clear_scan_data(db)
            print(f"Cleared {deleted_records} scan records and {deleted_logs} import logs")

        items = load_craft_resources(db, rng)
        sellers = build_seller_names(args.sellers, rng)
        records = generate_records(args.count, items, sellers, args.days, rng)

        affected_entities: set[uuid.UUID] = set(cleared_entities)
        saved_total = 0
        matched_total = 0

        for offset in range(0, len(records), args.batch_size):
            batch = records[offset : offset + args.batch_size]
            saved_count, matched_count, batch_entities = save_scan_batch(db, batch)
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

        print(
            f"Done: {saved_total} records, {matched_total} matched to wiki items, "
            f"{len(sellers)} sellers, {len(items)} craft resources"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
