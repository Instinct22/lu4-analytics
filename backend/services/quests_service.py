"""Load and filter the offline quests catalog built from local wiki HTML."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import settings

DEFAULT_LEVEL_MAX = 99
CATALOG_FILENAME = "quests_catalog.json"


def _catalog_candidates() -> list[Path]:
    root = Path(settings.datasets_path)
    return [
        root / CATALOG_FILENAME,
        Path(__file__).resolve().parents[2] / "data" / "datasets" / CATALOG_FILENAME,
    ]


def catalog_path() -> Path | None:
    for path in _catalog_candidates():
        if path.is_file():
            return path
    return None


@lru_cache(maxsize=1)
def _load_raw(mtime_ns: int, path_str: str) -> dict[str, Any]:
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"quests": []}


def load_catalog() -> dict[str, Any]:
    path = catalog_path()
    if path is None:
        return {"quests": [], "count": 0, "generated_at": None}
    st = path.stat()
    return _load_raw(st.st_mtime_ns, str(path.resolve()))


def clear_catalog_cache() -> None:
    _load_raw.cache_clear()


def effective_level_max(level_min: int | None, level_max: int | None) -> int | None:
    if level_max is not None:
        return level_max
    if level_min is not None:
        return DEFAULT_LEVEL_MAX
    return None


def quest_overlaps_range(
    level_min: int | None,
    level_max: int | None,
    filter_min: int,
    filter_max: int,
) -> bool:
    """True when quest level window intersects [filter_min, filter_max]."""
    if level_min is None and level_max is None:
        return True
    q_min = level_min if level_min is not None else 0
    q_max = effective_level_max(level_min, level_max)
    if q_max is None:
        q_max = DEFAULT_LEVEL_MAX
    return q_min <= filter_max and q_max >= filter_min


def _npc_brief(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "id": raw.get("id"),
        "name": raw.get("name") or "",
        "icon": raw.get("icon"),
    }


def quest_to_brief(raw: dict[str, Any]) -> dict[str, Any]:
    rewards = raw.get("rewards") or []
    return {
        "id": raw["id"],
        "slug": raw.get("slug") or "",
        "name": raw.get("name") or "",
        "level_min": raw.get("level_min"),
        "level_max": raw.get("level_max"),
        "description": raw.get("description") or "",
        "start_npc": _npc_brief(raw.get("start_npc")),
        "reward_count": len(rewards) if isinstance(rewards, list) else 0,
    }


def quest_to_detail(raw: dict[str, Any]) -> dict[str, Any]:
    rewards = []
    for r in raw.get("rewards") or []:
        if not isinstance(r, dict):
            continue
        rewards.append(
            {
                "item_id": r.get("item_id"),
                "name": r.get("name") or "",
                "grade": r.get("grade"),
                "icon": r.get("icon"),
                "qty": r.get("qty"),
            }
        )
    steps = []
    for s in raw.get("steps") or []:
        if not isinstance(s, dict):
            continue
        steps.append(
            {
                "title": s.get("title") or "",
                "text": s.get("text") or "",
                "images": list(s.get("images") or []),
            }
        )
    return {
        "id": raw["id"],
        "slug": raw.get("slug") or "",
        "name": raw.get("name") or "",
        "url": raw.get("url"),
        "source_url": raw.get("source_url"),
        "level_min": raw.get("level_min"),
        "level_max": raw.get("level_max"),
        "description": raw.get("description") or "",
        "start_npc": _npc_brief(raw.get("start_npc")),
        "rewards": rewards,
        "steps": steps,
    }


def list_quests(
    *,
    min_level: int | None = None,
    max_level: int | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog()
    quests = catalog.get("quests") or []
    query = (q or "").strip().lower()
    briefs: list[dict[str, Any]] = []
    for raw in quests:
        if not isinstance(raw, dict) or "id" not in raw:
            continue
        if min_level is not None and max_level is not None:
            if not quest_overlaps_range(raw.get("level_min"), raw.get("level_max"), min_level, max_level):
                continue
        if query:
            name = str(raw.get("name") or "").lower()
            desc = str(raw.get("description") or "").lower()
            npc = raw.get("start_npc") if isinstance(raw.get("start_npc"), dict) else {}
            npc_name = str(npc.get("name") or "").lower()
            if query not in name and query not in desc and query not in npc_name:
                continue
        briefs.append(quest_to_brief(raw))
    return {
        "quests": briefs,
        "count": len(briefs),
        "generated_at": catalog.get("generated_at"),
    }


def get_quest(quest_id: int) -> dict[str, Any] | None:
    catalog = load_catalog()
    for raw in catalog.get("quests") or []:
        if isinstance(raw, dict) and raw.get("id") == quest_id:
            return quest_to_detail(raw)
    return None
