from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DbSession, require_permission
from models.analytics import AnalyticsDataset
from models.raid import RaidBoss, RaidBossTimer

router = APIRouter()

DATASET_KEY = "raid_bosses"
DEFAULT_MAP = {
    "width": 1808,
    "height": 2658,
    "image": "/raid-map/map_lu4.webp",
    "flag": "/raid-map/flag.png",
}

require_read = require_permission("nav.raid_bosses")
require_write = require_permission("feature.raid_timers_write")


class TimerIn(BaseModel):
    killed_at: datetime | None = None


def _boss_json(boss: RaidBoss) -> dict:
    payload = boss.payload or {}
    return {
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
        "howToReach": payload.get("howToReach"),
        "skills": payload.get("skills") or [],
        "drops": payload.get("drops") or [],
    }


def _timer_json(timer: RaidBossTimer) -> dict:
    return {
        "bossId": timer.boss_external_id,
        "killedAt": timer.killed_at.isoformat(),
        "updatedAt": timer.updated_at.isoformat() if timer.updated_at else None,
    }


@router.get("/bosses", dependencies=[Depends(require_read)])
def list_bosses(db: DbSession):
    bosses = db.scalars(select(RaidBoss).order_by(RaidBoss.level, RaidBoss.name)).all()
    dataset = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == DATASET_KEY))
    blob = dataset.payload if dataset and isinstance(dataset.payload, dict) else {}
    return {
        "source": blob.get("source") or {},
        "map": blob.get("map") or DEFAULT_MAP,
        "bosses": [_boss_json(b) for b in bosses],
    }


@router.get("/timers", dependencies=[Depends(require_read)])
def list_timers(db: DbSession):
    timers = db.scalars(select(RaidBossTimer)).all()
    return {"timers": [_timer_json(t) for t in timers]}


@router.post("/timers/{boss_id}", dependencies=[Depends(require_write)])
def set_timer(boss_id: int, body: TimerIn, db: DbSession, user: CurrentUser):
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
    db.commit()
    db.refresh(timer)
    return _timer_json(timer)


@router.delete("/timers/{boss_id}", dependencies=[Depends(require_write)])
def clear_timer(boss_id: int, db: DbSession):
    timer = db.get(RaidBossTimer, boss_id)
    if timer is not None:
        db.delete(timer)
        db.commit()
    return {"bossId": boss_id, "cleared": True}
