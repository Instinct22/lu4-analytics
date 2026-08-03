from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession
from schemas.auth import CraftMonitorResponse, LevelRestrictionResponse
from services.admin_settings import get_craft_monitor, get_level_preset, get_level_restriction

router = APIRouter()


@router.get("/level-restriction", response_model=LevelRestrictionResponse)
def read_level_restriction(db: DbSession, _user: CurrentUser):
    bounds = get_level_restriction(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.get("/level-preset", response_model=LevelRestrictionResponse)
def read_level_preset(db: DbSession, _user: CurrentUser):
    bounds = get_level_preset(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.get("/craft-monitor", response_model=CraftMonitorResponse)
def read_craft_monitor(db: DbSession, _user: CurrentUser):
    value = get_craft_monitor(db)
    return CraftMonitorResponse(selectedIds=value["selectedIds"])
