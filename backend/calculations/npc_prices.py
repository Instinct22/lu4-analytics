"""NPC shop buy price derived from wiki sell price (NG/D gear only)."""

from __future__ import annotations

NPC_BUY_MULTIPLIER = 2.4
NPC_BUY_GRADES = frozenset({"NG", "D"})

GEAR_CATEGORY_PREFIXES = (
    "weapons/",
    "armors/",
    "other/jewelry",
)


def is_npc_buy_eligible(grade: str, category: str) -> bool:
    if grade not in NPC_BUY_GRADES:
        return False
    if not category:
        return False
    return any(category.startswith(prefix) for prefix in GEAR_CATEGORY_PREFIXES)


def compute_npc_buy(
    npc_sell: int | None,
    grade: str,
    category: str,
) -> int | None:
    if npc_sell is None or not is_npc_buy_eligible(grade, category):
        return None
    return round(npc_sell * NPC_BUY_MULTIPLIER)
