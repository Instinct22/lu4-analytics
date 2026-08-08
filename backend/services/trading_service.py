"""Shared trading inventory service: characters, lines, snapshots."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models.preferences import UserPreference
from models.trading import TradingCharacter, TradingInventoryLine, TradingSnapshot
from models.wiki import WikiEntity
from schemas.trading_inventory import (
    CharacterCreate,
    CharacterOut,
    CharacterUpdate,
    InventoryLineIn,
    InventoryLineOut,
    InventoryScanRequest,
    InventoryScanResponse,
    ItemCatalogHit,
    ItemSearchHit,
    WarehouseSyncRequest,
    WarehouseSyncResponse,
)
from services import craft_service, market_service
from services.name_matching import normalize_product_name, unescape_text

VALID_KINDS = frozenset({"bank", "merchant"})
VALID_TRADE_MODES = frozenset({"sell", "buy"})
MASTER_COIN_EXTERNAL_ID = 4037
MASTER_COIN_NAME = "Master Coin"
WALLET_ITEM_NAMES = frozenset({"adena", "master coin", "mastercoin", "mc"})
WAREHOUSE_ADENA_KEY = "adena"
WAREHOUSE_MASTER_COIN_KEY = "master_coin"
CRAFT_OWNED_SCOPE = "craft_owned"


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


def _catalog_matched(external_id: int) -> bool:
    return external_id >= 0


def _lines_out(lines: list[TradingInventoryLine]) -> list[InventoryLineOut]:
    return [
        InventoryLineOut(
            id=line.id,
            item_external_id=line.item_external_id,
            item_name=line.item_name,
            quantity=line.quantity,
            unit_price=_dec(line.unit_price),
            line_total=_line_total(line),
            catalog_matched=_catalog_matched(line.item_external_id),
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
    master = _dec(getattr(char, "master_coin", 0))
    master_price = _dec(getattr(char, "master_coin_price", 0))
    master_adena = master * master_price
    mode = char.trade_mode if char.trade_mode in VALID_TRADE_MODES else "sell"
    if char.kind != "merchant":
        mode = "sell"
    return CharacterOut(
        id=char.id,
        kind=char.kind,  # type: ignore[arg-type]
        nick=char.nick,
        clean_adena=clean,
        master_coin=master,
        master_coin_price=master_price,
        master_coin_adena=master_adena,
        description=char.description,
        trade_mode=mode,  # type: ignore[arg-type]
        is_main=bool(getattr(char, "is_main", False)) and char.kind == "bank",
        adena_in_items=sell_value,
        buy_cost=buy_cost,
        total_adena=clean + sell_value + master_adena - buy_cost,
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
        master_coin=Decimal("0"),
        master_coin_price=Decimal("0"),
        description=None,
        trade_mode="sell",
        is_main=False,
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
    char.master_coin = _dec(body.master_coin)
    char.master_coin_price = _dec(body.master_coin_price)
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
        .where(TradingCharacter.id == char.id)
    ).one()
    return _character_out(char)


def set_character_main(
    db: Session,
    character_id: uuid.UUID,
    is_main: bool,
    user_id: uuid.UUID,
) -> CharacterOut:
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == character_id)
    ).first()
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.kind != "bank":
        raise HTTPException(status_code=400, detail="Main можно выбрать только у персонажа Банка")

    if is_main:
        others = db.scalars(
            select(TradingCharacter).where(
                TradingCharacter.kind == "bank",
                TradingCharacter.is_main.is_(True),
                TradingCharacter.id != char.id,
            )
        ).all()
        for other in others:
            other.is_main = False

    char.is_main = bool(is_main)
    char.updated_by_user_id = user_id
    db.commit()
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == char.id)
    ).one()
    return _character_out(char)


def _get_main_bank(db: Session) -> TradingCharacter:
    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.kind == "bank", TradingCharacter.is_main.is_(True))
        .limit(1)
    ).first()
    if char is None:
        raise HTTPException(status_code=400, detail="Не выбран Main персонаж в Банке")
    return char


def _warehouse_wallet_value(payload: dict, key: str) -> Decimal:
    raw = payload.get(key, 0)
    try:
        value = Decimal(str(raw))
    except Exception:
        return Decimal("0")
    return value if value > 0 else Decimal("0")


def _warehouse_items(payload: dict) -> dict[int, int]:
    items: dict[int, int] = {}
    for key, raw in (payload or {}).items():
        if key in {WAREHOUSE_ADENA_KEY, WAREHOUSE_MASTER_COIN_KEY}:
            continue
        try:
            eid = int(key)
        except (TypeError, ValueError):
            continue
        if eid <= 0 or eid == MASTER_COIN_EXTERNAL_ID:
            continue
        try:
            qty = int(raw)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            items[eid] = items.get(eid, 0) + qty
    return items


def _build_warehouse_payload(
    items: dict[int, int],
    adena: Decimal,
    master_coin: Decimal,
) -> dict[str, int]:
    payload: dict[str, int] = {
        str(eid): int(qty)
        for eid, qty in sorted(items.items())
        if qty > 0 and eid > 0 and eid != MASTER_COIN_EXTERNAL_ID
    }
    adena_i = int(adena)
    master_i = int(master_coin)
    if adena_i > 0:
        payload[WAREHOUSE_ADENA_KEY] = adena_i
    if master_i > 0:
        payload[WAREHOUSE_MASTER_COIN_KEY] = master_i
    return payload


def _put_craft_owned(db: Session, user_id: uuid.UUID, payload: dict) -> dict:
    row = db.get(UserPreference, (user_id, CRAFT_OWNED_SCOPE))
    if row is None:
        row = UserPreference(user_id=user_id, scope=CRAFT_OWNED_SCOPE, payload=payload)
        db.add(row)
    else:
        row.payload = payload
    db.flush()
    return dict(row.payload or {})


def _name_for_external_id(db: Session, external_id: int) -> str:
    entity = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id == external_id)
        .limit(1)
    ).first()
    if entity is not None:
        return unescape_text(entity.display_name) or f"#{external_id}"

    materials = craft_service.resource_materials(db).get("materials") or []
    for material in materials:
        eid = material.get("id")
        name = (material.get("name") or "").strip()
        if eid is None or not name:
            continue
        if int(eid) == external_id:
            return name
    if external_id == MASTER_COIN_EXTERNAL_ID:
        return MASTER_COIN_NAME
    return f"#{external_id}"


def sync_warehouse(
    db: Session,
    user_id: uuid.UUID,
    body: WarehouseSyncRequest,
) -> WarehouseSyncResponse:
    char = _get_main_bank(db)

    if body.direction == "to_warehouse":
        items: dict[int, int] = {}
        for line in char.items or []:
            if (line.list_kind or "sell") != "sell":
                continue
            eid = int(line.item_external_id)
            qty = int(line.quantity or 0)
            if eid <= 0 or eid == MASTER_COIN_EXTERNAL_ID or qty <= 0:
                continue
            items[eid] = items.get(eid, 0) + qty

        adena = _dec(char.clean_adena)
        master = _dec(getattr(char, "master_coin", 0))
        payload = _build_warehouse_payload(items, adena, master)
        warehouse = _put_craft_owned(db, user_id, payload)
        char.updated_by_user_id = user_id
        db.commit()
        return WarehouseSyncResponse(
            direction="to_warehouse",
            character_id=char.id,
            character_nick=char.nick,
            item_count=len(items),
            adena=adena,
            master_coin=master,
            warehouse=warehouse,
            character=_character_out(char),
        )

    # to_bank: replace Main sell inventory + wallet from warehouse
    pref = db.get(UserPreference, (user_id, CRAFT_OWNED_SCOPE))
    owned = dict(pref.payload) if pref and isinstance(pref.payload, dict) else {}
    items = _warehouse_items(owned)
    adena = _warehouse_wallet_value(owned, WAREHOUSE_ADENA_KEY)
    master = _warehouse_wallet_value(owned, WAREHOUSE_MASTER_COIN_KEY)

    char.clean_adena = adena
    char.master_coin = master
    mc_prices = _unit_prices_for_ids(db, [MASTER_COIN_EXTERNAL_ID])
    market_mc_price = mc_prices.get(MASTER_COIN_EXTERNAL_ID, Decimal("0"))
    if market_mc_price > 0:
        char.master_coin_price = market_mc_price
    char.updated_by_user_id = user_id

    price_map = _unit_prices_for_ids(db, list(items.keys()))
    buy_kept = [line for line in list(char.items or []) if line.list_kind == "buy"]
    char.items.clear()
    db.flush()
    for line in buy_kept:
        char.items.append(line)

    sell_inputs = [
        InventoryLineIn(
            item_external_id=eid,
            item_name=_name_for_external_id(db, eid),
            quantity=qty,
            unit_price=price_map.get(eid, Decimal("0")),
        )
        for eid, qty in sorted(items.items())
    ]
    _append_lines(char, sell_inputs, "sell")
    db.commit()

    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == char.id)
    ).one()
    return WarehouseSyncResponse(
        direction="to_bank",
        character_id=char.id,
        character_nick=char.nick,
        item_count=len(items),
        adena=adena,
        master_coin=master,
        warehouse=_build_warehouse_payload(items, adena, master),
        character=_character_out(char),
    )


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
                "master_coin": str(c.master_coin),
                "master_coin_price": str(c.master_coin_price),
                "master_coin_adena": str(c.master_coin_adena),
                "description": c.description or "",
                "trade_mode": c.trade_mode,
                "is_main": bool(c.is_main),
                "adena_in_items": str(c.adena_in_items),
                "buy_cost": str(c.buy_cost),
                "total_adena": str(c.total_adena),
                "sell_items": [
                    {
                        "item_external_id": item.item_external_id,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "catalog_matched": item.catalog_matched,
                    }
                    for item in c.sell_items
                ],
                "buy_items": [
                    {
                        "item_external_id": item.item_external_id,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "catalog_matched": item.catalog_matched,
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
                        "catalog_matched": item.catalog_matched,
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
    user_id: uuid.UUID | None = None,
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


def _is_wallet_item_name(name: str) -> bool:
    norm = normalize_product_name(name)
    if norm in WALLET_ITEM_NAMES:
        return True
    compact = norm.replace(" ", "")
    return compact in {"mastercoin", "mc"}


def _custom_item_id(name: str) -> int:
    digest = hashlib.md5(name.casefold().encode("utf-8")).hexdigest()
    return -(int(digest[:8], 16) % 1_000_000_000) - 1


def _craft_resource_by_name(db: Session, normalized: str) -> tuple[int, str] | None:
    if not normalized:
        return None
    materials = craft_service.resource_materials(db).get("materials") or []
    for material in materials:
        eid = material.get("id")
        name = (material.get("name") or "").strip()
        if eid is None or not name:
            continue
        if normalize_product_name(name) == normalized:
            return int(eid), name
    if normalized in {"master coin", "mastercoin", "mc"}:
        return MASTER_COIN_EXTERNAL_ID, MASTER_COIN_NAME
    return None


def _resolve_inventory_item(db: Session, raw_name: str) -> tuple[int, str, bool]:
    """Return (external_id, display_name, catalog_matched)."""
    name = unescape_text(raw_name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Item name is required")

    normalized = normalize_product_name(name)

    entity = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id.is_not(None))
        .where(WikiEntity.name_normalized == normalized)
        .limit(1)
    ).first()
    if entity is not None and entity.external_id is not None:
        display = unescape_text(entity.display_name) or name
        return int(entity.external_id), display, True

    # Case-insensitive display_name fallback
    entity = db.scalars(
        select(WikiEntity)
        .where(WikiEntity.entity_type == "item")
        .where(WikiEntity.external_id.is_not(None))
        .where(func.lower(WikiEntity.display_name) == name.casefold())
        .limit(1)
    ).first()
    if entity is not None and entity.external_id is not None:
        display = unescape_text(entity.display_name) or name
        return int(entity.external_id), display, True

    craft_hit = _craft_resource_by_name(db, normalized)
    if craft_hit is not None:
        return craft_hit[0], craft_hit[1], True

    return _custom_item_id(name), name, False


def _find_character_by_nick(db: Session, nick: str) -> TradingCharacter | None:
    return db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(func.lower(TradingCharacter.nick) == nick.casefold())
        .limit(1)
    ).first()


def _unit_prices_for_ids(db: Session, external_ids: list[int]) -> dict[int, Decimal]:
    positive = sorted({eid for eid in external_ids if eid >= 0})
    if not positive:
        return {}
    prices = market_service.prices_by_ids(db, ",".join(str(eid) for eid in positive))
    result: dict[int, Decimal] = {}
    for eid in positive:
        row = prices.get(str(eid)) or {}
        raw = row.get("day_vwap")
        if raw is None:
            raw = row.get("last_price")
        result[eid] = _dec(raw) if raw is not None else Decimal("0")
    return result


def upsert_inventory_scan(db: Session, body: InventoryScanRequest) -> InventoryScanResponse:
    nick = body.name.strip()
    if not nick:
        raise HTTPException(status_code=400, detail="Nick is required")

    snapshot = create_snapshot(
        db,
        user_id=None,
        label=f"auto: inventory-scan {nick}",
    )

    char = _find_character_by_nick(db, nick)
    created = False
    if char is None:
        max_order = db.scalar(
            select(func.coalesce(func.max(TradingCharacter.sort_order), -1)).where(
                TradingCharacter.kind == "bank"
            )
        )
        char = TradingCharacter(
            id=uuid.uuid4(),
            kind="bank",
            nick=nick,
            clean_adena=Decimal("0"),
            master_coin=Decimal("0"),
            master_coin_price=Decimal("0"),
            description=None,
            trade_mode="sell",
            is_main=False,
            sort_order=int(max_order or -1) + 1,
            updated_by_user_id=None,
        )
        db.add(char)
        db.flush()
        created = True
        char = db.scalars(
            select(TradingCharacter)
            .options(selectinload(TradingCharacter.items))
            .where(TradingCharacter.id == char.id)
        ).one()

    char.clean_adena = _dec(body.adena)
    char.master_coin = _dec(body.master_coin)
    mc_prices = _unit_prices_for_ids(db, [MASTER_COIN_EXTERNAL_ID])
    market_mc_price = mc_prices.get(MASTER_COIN_EXTERNAL_ID, Decimal("0"))
    if market_mc_price > 0:
        char.master_coin_price = market_mc_price
    elif not getattr(char, "master_coin_price", None):
        char.master_coin_price = Decimal("0")
    char.updated_by_user_id = None

    # Aggregate quantities by resolved key (matched id or custom name)
    resolved: list[tuple[int, str, bool, int]] = []
    for item in body.items:
        raw_name = item.name.strip()
        if not raw_name or _is_wallet_item_name(raw_name):
            continue
        if item.count <= 0:
            continue
        external_id, display_name, matched = _resolve_inventory_item(db, raw_name)
        if external_id == MASTER_COIN_EXTERNAL_ID and matched:
            # Master Coin is a wallet field; skip inventory line
            continue
        if matched and normalize_product_name(display_name) == "adena":
            continue
        resolved.append((external_id, display_name, matched, item.count))

    # Merge duplicate resolved items
    merged: dict[tuple[int, str], tuple[int, str, bool, int]] = {}
    for external_id, display_name, matched, count in resolved:
        key = (external_id, display_name.casefold())
        prev = merged.get(key)
        if prev is None:
            merged[key] = (external_id, display_name, matched, count)
        else:
            merged[key] = (prev[0], prev[1], prev[2], prev[3] + count)

    lines_data = list(merged.values())
    price_map = _unit_prices_for_ids(db, [row[0] for row in lines_data])

    # Clear sell inventory, keep buy lines
    buy_kept = [line for line in list(char.items or []) if line.list_kind == "buy"]
    char.items.clear()
    db.flush()
    for line in buy_kept:
        char.items.append(line)

    sell_inputs: list[InventoryLineIn] = []
    matched_count = 0
    unmatched_count = 0
    for external_id, display_name, matched, quantity in lines_data:
        if matched:
            matched_count += 1
        else:
            unmatched_count += 1
        sell_inputs.append(
            InventoryLineIn(
                item_external_id=external_id,
                item_name=display_name,
                quantity=quantity,
                unit_price=price_map.get(external_id, Decimal("0")),
            )
        )

    _append_lines(char, sell_inputs, "sell")
    db.commit()

    char = db.scalars(
        select(TradingCharacter)
        .options(selectinload(TradingCharacter.items))
        .where(TradingCharacter.id == char.id)
    ).one()

    return InventoryScanResponse(
        character=_character_out(char),
        snapshot_id=snapshot.id,
        created=created,
        matched_count=matched_count,
        unmatched_count=unmatched_count,
    )
