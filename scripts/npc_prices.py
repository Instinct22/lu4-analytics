"""Re-export NPC buy helpers for dataset build scripts."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from calculations.npc_prices import (  # noqa: E402
    NPC_BUY_GRADES,
    NPC_BUY_MULTIPLIER,
    compute_npc_buy,
    is_npc_buy_eligible,
)


def apply_npc_buy_to_item(item: dict[str, Any]) -> None:
    category = item.get("category") or ""
    if not category:
        from craft_catalog.categories import resolve_category

        category = resolve_category(item.get("type") or "", item.get("name") or "")
    item["npc_buy"] = compute_npc_buy(
        item.get("npc_sell"),
        item.get("grade") or "",
        category,
    )
