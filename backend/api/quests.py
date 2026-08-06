from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import require_permission
from models.user import User
from services import quests_service

router = APIRouter()

QuestsUser = Annotated[User, Depends(require_permission("nav.quests"))]


@router.get("")
def list_quests(
    user: QuestsUser,
    min_level: int | None = Query(None, ge=0, le=99),
    max_level: int | None = Query(None, ge=0, le=99),
    q: str | None = Query(None, max_length=200),
):
    if (min_level is None) ^ (max_level is None):
        raise HTTPException(status_code=400, detail="Provide both min_level and max_level, or neither")
    if min_level is not None and max_level is not None and min_level > max_level:
        raise HTTPException(status_code=400, detail="min_level cannot exceed max_level")
    return quests_service.list_quests(min_level=min_level, max_level=max_level, q=q)


@router.get("/{quest_id}")
def get_quest(quest_id: int, user: QuestsUser):
    quest = quests_service.get_quest(quest_id)
    if quest is None:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest
