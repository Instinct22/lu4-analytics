import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.deps import CurrentUser, DbSession, require_permission, require_raid_life_read, user_has_permission
from schemas.raid_life import RaidBossLifeResponse
from services.raid_timers import build_boss_life_list
from core.client_ip import client_ip
from models.analytics import AnalyticsDataset
from models.raid import RaidBoss, RaidBossNote, RaidBossTimer
from models.raid_timer_log import RaidTimerLog
from services.admin_settings import get_raid_hidden, set_raid_hidden

router = APIRouter()

DATASET_KEY = "raid_bosses"
DEFAULT_MAP = {
    "width": 1808,
    "height": 2658,
    "image": "/raid-map/map_lu4.webp",
    "flag": "/raid-map/flag.png",
}

require_read = require_permission("nav.raid_bosses")
require_timers_view = require_permission("feature.raid_timers_view")
require_write = require_permission("feature.raid_timers_write")
require_visibility = require_permission("feature.raid_visibility")


class TimerIn(BaseModel):
    killed_at: datetime | None = None


class RaidVisibilityIn(BaseModel):
    hiddenIds: list[int]


class NoteIn(BaseModel):
    note: str = Field(default="", max_length=120)


NOTE_MAX_LEN = 120


def _log_timer_action(
    db: DbSession,
    *,
    user: CurrentUser,
    request: Request,
    boss: RaidBoss,
    action: str,
    killed_at: datetime | None = None,
) -> None:
    db.add(
        RaidTimerLog(
            id=uuid.uuid4(),
            user_id=user.id,
            username=user.username,
            ip_address=client_ip(request),
            boss_external_id=boss.external_id,
            boss_name=boss.name,
            action=action,
            killed_at=killed_at,
        )
    )


def _boss_json(boss: RaidBoss, *, include_route: bool) -> dict:
    payload = boss.payload or {}
    data = {
        "id": boss.external_id,
        "name": boss.name,
        "level": boss.level,
        "x": boss.map_x,
        "y": boss.map_y,
        "image": boss.image_url,
        "wikiUrl": boss.wiki_url,
        "location": boss.location,
        "respawn": boss.respawn_raw,
        "respawnMinSec": boss.respawn_min_sec,
        "respawnMaxSec": boss.respawn_max_sec,
        "stats": payload.get("stats") or {},
        "lore": payload.get("lore"),
        "skills": payload.get("skills") or [],
        "drops": payload.get("drops") or [],
        "spoils": payload.get("spoils") or [],
        "race": payload.get("race"),
        "bossType": payload.get("bossType"),
        "spawnPoints": payload.get("spawnPoints") or [],
        "minions": payload.get("minions") or [],
        "soulCrystals": payload.get("soulCrystals") or [],
        "detailsPending": payload.get("detailsPending", False),
    }
    if include_route:
        data["howToReach"] = payload.get("howToReach")
    return data


def _timer_json(timer: RaidBossTimer) -> dict:
    return {
        "bossId": timer.boss_external_id,
        "killedAt": timer.killed_at.isoformat(),
        "updatedAt": timer.updated_at.isoformat() if timer.updated_at else None,
    }


def _note_json(note: RaidBossNote) -> dict:
    return {
        "bossId": note.boss_external_id,
        "note": note.note or "",
    }


@router.get("/bosses", dependencies=[Depends(require_read)])
def list_bosses(db: DbSession, user: CurrentUser):
    include_route = user_has_permission(db, user, "feature.raid_route")
    bosses = db.scalars(select(RaidBoss).order_by(RaidBoss.level, RaidBoss.name)).all()
    dataset = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == DATASET_KEY))
    blob = dataset.payload if dataset and isinstance(dataset.payload, dict) else {}
    return {
        "source": blob.get("source") or {},
        "map": blob.get("map") or DEFAULT_MAP,
        "bosses": [_boss_json(b, include_route=include_route) for b in bosses],
    }


@router.get("/timers", dependencies=[Depends(require_read)])
def list_timers(db: DbSession, user: CurrentUser):
    if not user_has_permission(db, user, "feature.raid_timers_view"):
        return {"timers": []}
    timers = db.scalars(select(RaidBossTimer)).all()
    return {"timers": [_timer_json(t) for t in timers]}


@router.get("/boss-life", response_model=RaidBossLifeResponse)
def list_boss_life(db: DbSession, _auth=Depends(require_raid_life_read())):
    return RaidBossLifeResponse(bosses=build_boss_life_list(db))


@router.post("/timers/{boss_id}", dependencies=[Depends(require_write)])
def set_timer(boss_id: int, body: TimerIn, request: Request, db: DbSession, user: CurrentUser):
    boss = db.get(RaidBoss, boss_id)
    if boss is None:
        raise HTTPException(status_code=404, detail="Boss not found")
    if boss.respawn_min_sec is None:
        raise HTTPException(status_code=400, detail="Boss has no respawn window")

    killed_at = body.killed_at or datetime.now(timezone.utc)
    if killed_at.tzinfo is None:
        killed_at = killed_at.replace(tzinfo=timezone.utc)
    if killed_at > datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Kill time is in the future")

    timer = db.get(RaidBossTimer, boss_id)
    if timer is None:
        timer = RaidBossTimer(boss_external_id=boss_id)
        db.add(timer)
    timer.killed_at = killed_at
    timer.set_by_user_id = user.id
    _log_timer_action(
        db,
        user=user,
        request=request,
        boss=boss,
        action="set",
        killed_at=killed_at,
    )
    db.commit()
    db.refresh(timer)
    return _timer_json(timer)


@router.delete("/timers/{boss_id}", dependencies=[Depends(require_write)])
def clear_timer(boss_id: int, request: Request, db: DbSession, user: CurrentUser):
    boss = db.get(RaidBoss, boss_id)
    timer = db.get(RaidBossTimer, boss_id)
    if timer is not None:
        if boss is not None:
            _log_timer_action(db, user=user, request=request, boss=boss, action="clear")
        db.delete(timer)
        db.commit()
    return {"bossId": boss_id, "cleared": True}


@router.get("/notes", dependencies=[Depends(require_read)])
def list_notes(db: DbSession, user: CurrentUser):
    if not user_has_permission(db, user, "feature.raid_timers_view"):
        return {"notes": []}
    notes = db.scalars(select(RaidBossNote)).all()
    return {"notes": [_note_json(n) for n in notes if n.note]}


@router.put("/notes/{boss_id}", dependencies=[Depends(require_write)])
def set_note(boss_id: int, body: NoteIn, db: DbSession, user: CurrentUser):
    boss = db.get(RaidBoss, boss_id)
    if boss is None:
        raise HTTPException(status_code=404, detail="Boss not found")

    text = body.note.strip()
    if len(text) > NOTE_MAX_LEN:
        raise HTTPException(status_code=400, detail=f"Note exceeds {NOTE_MAX_LEN} characters")

    row = db.get(RaidBossNote, boss_id)
    if not text:
        if row is not None:
            db.delete(row)
            db.commit()
        return {"bossId": boss_id, "note": ""}

    if row is None:
        row = RaidBossNote(boss_external_id=boss_id)
        db.add(row)
    row.note = text
    row.updated_by_user_id = user.id
    db.commit()
    db.refresh(row)
    return _note_json(row)


@router.get("/visibility", dependencies=[Depends(require_read)])
def get_visibility(db: DbSession):
    """Global hidden raid-boss ids shared by all accounts."""
    return get_raid_hidden(db)


@router.put("/visibility", dependencies=[Depends(require_visibility)])
def update_visibility(body: RaidVisibilityIn, db: DbSession):
    value = set_raid_hidden(db, body.hiddenIds)
    db.commit()
    return value
