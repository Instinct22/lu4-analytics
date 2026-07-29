"""Load raid boss travel routes keyed by NPC external id."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from config import settings


def _routes_file() -> Path | None:
    candidates = [
        Path(settings.datasets_path).parent / "raid-bosses" / "how_to_reach.json",
        Path(__file__).resolve().parents[2] / "data" / "raid-bosses" / "how_to_reach.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


@lru_cache(maxsize=1)
def load_how_to_reach() -> dict[str, str]:
    path = _routes_file()
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v}


def how_to_reach_for(boss_id: int | None, boss: dict) -> str | None:
    direct = boss.get("howToReach")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    if boss_id is None:
        return None
    return load_how_to_reach().get(str(boss_id))
