from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession
from schemas.auth import LevelRestrictionResponse
from services.admin_settings import get_level_preset, get_level_restriction

router = APIRouter()


@router.get("/level-restriction", response_model=LevelRestrictionResponse)
def read_level_restriction(db: DbSession, _user: CurrentUser):
    bounds = get_level_restriction(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.get("/level-preset", response_model=LevelRestrictionResponse)
def read_level_preset(db: DbSession, _user: CurrentUser):
    bounds = get_level_preset(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])
