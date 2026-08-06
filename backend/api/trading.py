"""HTTP API for shared trading inventory (bank / merchants / snapshots)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from api.deps import CurrentUser, DbSession, require_permission, verify_api_key
from schemas.trading_inventory import (
    CharacterCreate,
    CharacterOut,
    CharacterUpdate,
    CharactersResponse,
    InventoryScanRequest,
    InventoryScanResponse,
    ItemCatalogResponse,
    ItemSearchResponse,
    SnapshotCreate,
    SnapshotDetailResponse,
    SnapshotListItem,
    SnapshotsListResponse,
)
from services import trading_service

router = APIRouter()

require_read = require_permission("nav.trading")
require_write = require_permission("feature.trading_write")


@router.post(
    "/inventory-scan",
    response_model=InventoryScanResponse,
    dependencies=[Depends(verify_api_key)],
)
def inventory_scan(body: InventoryScanRequest, db: DbSession):
    return trading_service.upsert_inventory_scan(db, body)


@router.get("/characters", response_model=CharactersResponse, dependencies=[Depends(require_read)])
def list_characters(db: DbSession):
    return CharactersResponse(characters=trading_service.list_characters(db))


@router.post(
    "/characters",
    response_model=CharacterOut,
    dependencies=[Depends(require_write)],
)
def create_character(body: CharacterCreate, db: DbSession, user: CurrentUser):
    return trading_service.create_character(db, body, user.id)


@router.put(
    "/characters/{character_id}",
    response_model=CharacterOut,
    dependencies=[Depends(require_write)],
)
def update_character(
    character_id: uuid.UUID,
    body: CharacterUpdate,
    db: DbSession,
    user: CurrentUser,
):
    return trading_service.update_character(db, character_id, body, user.id)


@router.delete(
    "/characters/{character_id}",
    status_code=204,
    dependencies=[Depends(require_write)],
)
def delete_character(character_id: uuid.UUID, db: DbSession):
    trading_service.delete_character(db, character_id)


@router.get(
    "/item-catalog",
    response_model=ItemCatalogResponse,
    dependencies=[Depends(require_read)],
)
def item_catalog(db: DbSession):
    return ItemCatalogResponse(items=trading_service.item_catalog(db))


@router.get(
    "/item-search",
    response_model=ItemSearchResponse,
    dependencies=[Depends(require_read)],
)
def item_search(
    db: DbSession,
    q: str = Query(min_length=1),
    limit: int = Query(30, ge=1, le=100),
):
    return ItemSearchResponse(items=trading_service.search_items(db, q, limit))


@router.get(
    "/snapshots",
    response_model=SnapshotsListResponse,
    dependencies=[Depends(require_read)],
)
def list_snapshots(db: DbSession):
    rows = trading_service.list_snapshots(db)
    return SnapshotsListResponse(
        snapshots=[
            SnapshotListItem(id=s.id, created_at=s.created_at, label=s.label) for s in rows
        ]
    )


@router.post(
    "/snapshots",
    response_model=SnapshotDetailResponse,
    dependencies=[Depends(require_write)],
)
def create_snapshot(body: SnapshotCreate, db: DbSession, user: CurrentUser):
    snap = trading_service.create_snapshot(db, user.id, body.label)
    return SnapshotDetailResponse(
        id=snap.id,
        created_at=snap.created_at,
        label=snap.label,
        payload=snap.payload or {},
    )


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotDetailResponse,
    dependencies=[Depends(require_read)],
)
def get_snapshot(snapshot_id: uuid.UUID, db: DbSession):
    snap = trading_service.get_snapshot(db, snapshot_id)
    return SnapshotDetailResponse(
        id=snap.id,
        created_at=snap.created_at,
        label=snap.label,
        payload=snap.payload or {},
    )
