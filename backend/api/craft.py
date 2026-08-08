from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import DbSession, require_any_permission, require_permission
from models.user import User
from services import craft_service

router = APIRouter()

CatalogUser = Annotated[User, Depends(require_any_permission("nav.craft", "nav.items"))]
ResourcesUser = Annotated[User, Depends(require_permission("nav.resources"))]
PricesUser = Annotated[User, Depends(require_permission("feature.craft_prices"))]
AppraisalUser = Annotated[User, Depends(require_permission("feature.craft_appraisal"))]


@router.get("/catalog")
def get_catalog(db: DbSession, user: CatalogUser):
    return craft_service.catalog(db)


@router.get("/items/{item_id}")
def get_item(item_id: int, db: DbSession, user: CatalogUser):
    item = craft_service.item_detail(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/recipes/{product_id}")
def get_recipes(product_id: int, db: DbSession, user: CatalogUser):
    return craft_service.recipe_closure(db, product_id)


@router.get("/materials/{material_id}/usage")
def get_material_usage(material_id: int, db: DbSession, user: CatalogUser):
    return {"material_id": material_id, "products": craft_service.material_usage(db, material_id)}


@router.get("/resources")
def get_resources(db: DbSession, user: ResourcesUser):
    return craft_service.resource_materials(db)


# Declared before /resources/{material_id}/sources so "npc" is not parsed as an id.
@router.get("/resources/npc/{npc_id}")
def get_npc_materials(npc_id: int, db: DbSession, user: ResourcesUser):
    return craft_service.npc_materials(db, npc_id)


@router.get("/resources/{material_id}/sources")
def get_material_sources(material_id: int, db: DbSession, user: ResourcesUser):
    return craft_service.material_sources(db, material_id)


@router.get("/profitability")
def get_profitability(
    db: DbSession,
    user: PricesUser,
    limit: int = Query(100, ge=1, le=500),
    min_margin: float | None = Query(None),
):
    return craft_service.profitability(db, limit=limit, min_margin=min_margin)


@router.get("/appraisal")
def get_appraisal(
    db: DbSession,
    user: AppraisalUser,
    grade: str = Query("C", pattern="^(NG|D|C|B|A|S)$"),
    item_type: str = Query("weapon", alias="type", pattern="^(weapon|armor|jewelry)$"),
    limit: int = Query(100, ge=1, le=500),
):
    return craft_service.appraisal(db, grade=grade, item_type=item_type, limit=limit)
