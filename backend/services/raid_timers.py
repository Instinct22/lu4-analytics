"""Raid boss timer phase evaluation (mirrors frontend/src/lib/raidTimers.ts)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.raid import RaidBoss, RaidBossTimer
from services.admin_settings import get_raid_hidden

TimerPhase = Literal["idle", "waiting", "soon", "window", "overdue"]
LifeStatus = Literal["yes", "no"]

SOON_SEC = 30 * 60


def evaluate_timer_phase(
    killed_at: datetime,
    min_sec: int,
    max_sec: int,
    now: datetime | None = None,
) -> TimerPhase:
    if now is None:
        now = datetime.now(timezone.utc)
    if killed_at.tzinfo is None:
        killed_at = killed_at.replace(tzinfo=timezone.utc)

    min_at = killed_at.timestamp() + min_sec
    max_at = killed_at.timestamp() + max_sec
    now_ts = now.timestamp()
    remaining_to_min = min_at - now_ts

    if now_ts >= max_at:
        return "overdue"
    if now_ts >= min_at:
        return "window"
    if remaining_to_min <= SOON_SEC:
        return "soon"
    return "waiting"


def life_from_phase(phase: TimerPhase) -> LifeStatus:
    if phase in ("soon", "window", "overdue"):
        return "yes"
    return "no"


def build_boss_life_list(db: Session, *, now: datetime | None = None) -> list[dict[str, str]]:
    if now is None:
        now = datetime.now(timezone.utc)

    hidden_ids = set(get_raid_hidden(db).get("hiddenIds") or [])
    bosses = db.scalars(select(RaidBoss).order_by(RaidBoss.level, RaidBoss.name)).all()
    timers = {
        t.boss_external_id: t
        for t in db.scalars(select(RaidBossTimer)).all()
    }

    result: list[dict[str, str]] = []
    for boss in bosses:
        if boss.external_id in hidden_ids:
            continue

        phase: TimerPhase = "idle"
        timer = timers.get(boss.external_id)
        if (
            timer is not None
            and boss.respawn_min_sec is not None
            and boss.respawn_max_sec is not None
        ):
            phase = evaluate_timer_phase(
                timer.killed_at,
                boss.respawn_min_sec,
                boss.respawn_max_sec,
                now,
            )

        result.append({"name": boss.name, "life": life_from_phase(phase)})

    return result
