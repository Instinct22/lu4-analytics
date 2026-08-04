"""Shared trading inventory service: characters, lines, snapshots."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models.trading import TradingCharacter, TradingInventoryLine, TradingSnapshot
from models.wiki import WikiEntity
from schemas.trading_inventory import (
    CharacterCreate,
    CharacterOut,
    CharacterUpdate,
    InventoryLineOut,
    ItemCatalogHit,
    ItemSearchHit,
)
from services import craft_service
from services.name_matching import unescape_text

VALID_KINDS = frozenset({"bank", "merchant"})
VALID_TRADE_MODES = frozenset({"sell", "buy"})
MASTER_COIN_EXTERNAL_ID = 4037
MASTER_COIN_NAME = "Master Coin"


def _dec(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _line_total(line: TradingInventoryLine | InventoryLineOut) -> Decimal:
    return _dec(line.quantity) * _dec(line.unit_price)


def _adena_sum(lines: list) -> Decimal:
    total = Decimal("0")
    for line in lines:
        total += _line_total(line)
    return total


def _lines_out(lines: list[TradingInventoryLine]) -> list[InventoryLineOut]:
    return [
        InventoryLineOut(
            id=line.id,
            item_external_id=line.item_external_id,
            item_name=line.item_name,
            quantity=line.quantity,
            unit_price=_dec(line.unit_price),
            line_total=_line_total(line),
        )
        for line in lines
    ]


def _character_out(char: TradingCharacter) -> CharacterOut:
    all_lines = list(char.items or [])
    sell_lines = [line for line in all_lines if (line.list_kind or "sell") == "sell"]
    buy_lines = [line for line in all_lines if line.list_kind == "buy"]
    sell_out = _lines_out(sell_lines)
    buy_out = _lines_out(buy_lines)
    sell_value = _adena_sum(sell_out)
    buy_cost = _adena_sum(buy_out)
    clean = _dec(char.clean_adena)
    mode = char.trade_mode if char.trade_mode in VALID_TRADE_MODES else "sell"
    if char.kind != "merchant":
        mode = "sell"
    return CharacterOut(
        id=char.id,
        kind=char.kind,  # type: ignore[arg-type]
        nick=char.nick,
        clean_adena=clean,
        description=char.description,
        trade_mode=mode,  # type: ignore[arg-type]
        adena_in_items=sell_value,
        buy_cost=buy_cost,
        total_adena=clean + sell_value - buy_cost,
        sort_order=char.sort_order,
        updated_at=char.updated_at,
        sell_items=sell_out,
        buy_items=buy_out,
        items=buy_out if mode == "buy" else sell_out,
    )


def list_characters(db: Session) -> list[CharacterOut]:
    rows = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .order_by(TradingCharacter.kind, TradingCharacter.sort_order, TradingCharacter.nick)
    ).all()
    return [_character_out(c) for c in rows]


def create_character(db: Session, body: CharacterCreate, user_id: uuid.UUID) -> CharacterOut:
    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail="Invalid kind")
    nick = body.nick.strip()
    if not nick:
        raise HTTPException(status_code=400, detail="Nick is required")

    max_order = db.scalar(
        select(func.coalesce(func.max(TradingCharacter.sort_order), -1)).where(
            TradingCharacter.kind == body.kind
        )
    )
    char = TradingCharacter(
        id=uuid.uuid4(),
        kind=body.kind,
        nick=nick,
        clean_adena=Decimal("0"),
        description=None,
        trade_mode="sell",
        sort_order=int(max_order or -1) + 1,
        updated_by_user_id=user_id,
    )
    db.add(char)
    db.commit()
    db.refresh(char)
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == char.id)
    ).one()
    return _character_out(char)


def delete_character(db: Session, character_id: uuid.UUID) -> None:
    char = db.get(TradingCharacter, character_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(char)
    db.commit()


def _append_lines(
    char: TradingCharacter,
    lines: list,
    list_kind: str,
) -> None:
    for idx, line in enumerate(lines):
        name = line.item_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Item name is required")
        char.items.append(
            TradingInventoryLine(
                id=uuid.uuid4(),
                character_id=char.id,
                item_external_id=line.item_external_id,
                item_name=name,
                quantity=line.quantity,
                unit_price=_dec(line.unit_price),
                list_kind=list_kind,
                sort_order=idx,
            )
        )


def update_character(
    db: Session,
    character_id: uuid.UUID,
    body: CharacterUpdate,
    user_id: uuid.UUID,
) -> CharacterOut:
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == character_id)
    ).first()
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")

    mode = body.trade_mode if body.trade_mode in VALID_TRADE_MODES else "sell"
    if char.kind != "merchant":
        mode = "sell"

    char.clean_adena = _dec(body.clean_adena)
    desc = body.description.strip() if body.description else None
    char.description = desc or None
    char.trade_mode = mode
    char.updated_by_user_id = user_id

    char.items.clear()
    db.flush()
    _append_lines(char, body.sell_items, "sell")
    if char.kind == "merchant":
        _append_lines(char, body.buy_items, "buy")

    db.commit()
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == character_id)
    ).one()
    return _character_out(char)


def search_items(db: Session, q: str, limit: int = 30) -> list[ItemSearchHit]:
    q = q.strip()
    if not q:
        return []
    pattern = f"%{q}%"
    rows = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id.is_not(None))
        .where(
            or_(
                WikiEntity.display_name.ilike(pattern),
                WikiEntity.name_normalized.ilike(pattern),
            )
        )
        .order_by(WikiEntity.display_name)
        .limit(limit)
    ).all()
    return [
        ItemSearchHit(
            external_id=int(e.external_id),
            display_name=unescape_text(e.display_name),
        )
        for e in rows
        if e.external_id is not None
    ]


def item_catalog(db: Session) -> list[ItemCatalogHit]:
    """Full browse list: craft resources first, then all other wiki items."""
    materials = craft_service.resource_materials(db).get("materials") or []
    resource_ids: set[int] = set()
    resources: list[ItemCatalogHit] = []

    for material in materials:
        eid = material.get("id")
        name = (material.get("name") or "").strip()
        if eid is None or not name:
            continue
        eid_i = int(eid)
        if eid_i in resource_ids:
            continue
        resource_ids.add(eid_i)
        resources.append(
            ItemCatalogHit(external_id=eid_i, display_name=name, group="resource")
        )

    if MASTER_COIN_EXTERNAL_ID not in resource_ids:
        resources.append(
            ItemCatalogHit(
                external_id=MASTER_COIN_EXTERNAL_ID,
                display_name=MASTER_COIN_NAME,
                group="resource",
            )
        )
        resource_ids.add(MASTER_COIN_EXTERNAL_ID)

    resources.sort(key=lambda row: row.display_name.casefold())

    wiki_rows = db.execute(
        select(WikiEntity.external_id, WikiEntity.display_name)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id.is_not(None))
        .order_by(WikiEntity.display_name)
    ).all()

    others: list[ItemCatalogHit] = []
    seen: set[int] = set(resource_ids)
    for eid, name in wiki_rows:
        if eid is None or eid in seen:
            continue
        seen.add(int(eid))
        others.append(
            ItemCatalogHit(
                external_id=int(eid),
                display_name=unescape_text(name or ""),
                group="item",
            )
        )

    return resources + others


def _snapshot_payload(db: Session) -> dict:
    characters = list_characters(db)
    return {
        "characters": [
            {
                "id": str(c.id),
                "kind": c.kind,
                "nick": c.nick,
                "clean_adena": str(c.clean_adena),
                "description": c.description or "",
                "trade_mode": c.trade_mode,
                "adena_in_items": str(c.adena_in_items),
                "buy_cost": str(c.buy_cost),
                "total_adena": str(c.total_adena),
                "sell_items": [
                    {
                        "item_external_id": item.item_external_id,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in c.sell_items
                ],
                "buy_items": [
                    {
                        "item_external_id": item.item_external_id,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in c.buy_items
                ],
                # legacy field for older snapshot viewers
                "items": [
                    {
                        "item_external_id": item.item_external_id,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in c.items
                ],
            }
            for c in characters
        ]
    }


def list_snapshots(db: Session) -> list[TradingSnapshot]:
    return list(
        db.scalars(select(TradingSnapshot).order_by(TradingSnapshot.created_at.desc())).all()
    )


def create_snapshot(
    db: Session,
    user_id: uuid.UUID,
    label: str | None = None,
) -> TradingSnapshot:
    snap = TradingSnapshot(
        id=uuid.uuid4(),
        created_by_user_id=user_id,
        label=(label.strip() if label else None) or None,
        payload=_snapshot_payload(db),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def get_snapshot(db: Session, snapshot_id: uuid.UUID) -> TradingSnapshot:
    snap = db.get(TradingSnapshot, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap
