from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import DbSession, require_any_permission
from models.user import User
from services import items_service

router = APIRouter()

ItemsUser = Annotated[User, Depends(require_any_permission("nav.craft", "nav.items"))]


@router.get("/catalog")
def get_catalog(
    db: DbSession,
    user: ItemsUser,
    section: str | None = Query(None, pattern="^(gear|other|excluded)$"),
):
    return items_service.catalog(db, section=section)


@router.get("/browse")
def get_browse(db: DbSession, user: ItemsUser):
    """Aggregated Items-page payload (gear + set slice + duals)."""
    return items_service.browse(db)


@router.get("/{item_id}")
def get_item(item_id: int, db: DbSession, user: ItemsUser):
    item = items_service.item_detail(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/{item_id}/sources")
def get_item_sources(item_id: int, db: DbSession, user: ItemsUser):
    sources = items_service.item_sources(db, item_id)
    if sources is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return sources
