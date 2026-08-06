#!/usr/bin/env python3
"""Seed market records for armor/jewelry sealed + unseal class variants."""
from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import delete, or_, select

from calculations.price_stats import recalculate_item_statistics
from database import SessionLocal
from models.item_encyclopedia import ItemEncyclopedia
from models.market import ImportLog, MarketRecord
from schemas.market_scan import ScanPrice, ScanRecord
from seed_market_scan import ACTIONS, CURRENCIES, build_seller_names, random_price
from services.market_scan_service import save_scan_record
from services.name_matching import clean_display_name

SOURCE = "gear_variants_seed"


def load_templates(db) -> list[tuple[str, str]]:
    """Return (market_name, grade) pairs for sealed + unseal armor/jewelry."""
    rows = db.scalars(
        select(ItemEncyclopedia).where(
            ItemEncyclopedia.section == "gear",
            or_(
                ItemEncyclopedia.type.like("Armor%"),
                ItemEncyclopedia.type.like("Accessory%"),
            ),
        )
    ).all()
    out: list[tuple[str, str]] = []
    for enc in rows:
        name = clean_display_name(enc.name)
        if not name:
            continue
        grade = (enc.grade or "").upper()
        payload = enc.payload if isinstance(enc.payload, dict) else {}
        if name.startswith("Sealed "):
            out.append((name, grade))
            # Bare unsealed jewelry/armor base (market: "Phoenix Ring", not only class pieces)
            bare = name[len("Sealed ") :].strip()
            if bare:
                out.append((bare, grade))
            for variant in payload.get("unseal_variants") or []:
                if not isinstance(variant, dict):
                    continue
                vname = clean_display_name(str(variant.get("name") or ""))
                if vname:
                    out.append((vname, grade))
        elif "Accessory" in (enc.type or ""):
            out.append((name, grade))
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, grade in out:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, grade))
    if not unique:
        raise RuntimeError("No armor/jewelry templates found. Import encyclopedia first.")
    return unique


def build_name(base: str, rng: random.Random) -> str:
    enchant = None
    if rng.random() < 0.55:
        enchant = rng.randint(1, 12)
    # Occasional apostrophe drop like the game API
    name = base.replace("'", "") if rng.random() < 0.5 else base
    if enchant is not None:
        return f"+{enchant} {name}"
    return name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--sellers", type=int, default=120)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--seed", type=int, default=77)
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    db = SessionLocal()
    try:
        if args.clear:
            log_ids = db.scalars(select(ImportLog.id).where(ImportLog.source == SOURCE)).all()
            if log_ids:
                db.execute(delete(MarketRecord).where(MarketRecord.import_log_id.in_(log_ids)))
            db.execute(delete(ImportLog).where(ImportLog.source == SOURCE))
            db.commit()
            print("Cleared prior gear_variants_seed data")

        templates = load_templates(db)
        print(f"Loaded {len(templates)} armor/jewelry name templates")
        sellers = build_seller_names(args.sellers, rng)
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=args.days)

        log = ImportLog(source=SOURCE, status="success")
        db.add(log)
        db.flush()

        matched = 0
        affected: set[uuid.UUID] = set()
        for _ in range(args.count):
            base, grade = rng.choice(templates)
            item = build_name(base, rng)
            price_base = Decimal(rng.randint(50_000, 5_000_000))
            if grade in {"A", "S"}:
                price_base = Decimal(rng.randint(1_000_000, 20_000_000))
            action = rng.choice(ACTIONS)
            currency = rng.choice(CURRENCIES)
            record = ScanRecord(
                action=action,
                name=rng.choice(sellers),
                item=item,
                count=rng.randint(1, 3),
                price=ScanPrice(
                    amount=random_price(price_base, rng, currency, action),
                    currency=currency,
                ),
                timestamp=start + timedelta(seconds=rng.randint(0, args.days * 24 * 3600)),
            )
            market_record, is_matched = save_scan_record(db, record, import_log_id=log.id)
            if is_matched and market_record.entity_id:
                matched += 1
                affected.add(market_record.entity_id)

        log.records_count = args.count
        log.matched_count = matched
        db.commit()

        for entity_id in affected:
            recalculate_item_statistics(db, entity_id)
        db.commit()
        print(f"Done: {args.count} records, {matched} matched, {len(affected)} entities")
    finally:
        db.close()


if __name__ == "__main__":
    main()
