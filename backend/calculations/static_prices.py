"""Fixed unit prices for items without reliable market data."""

from __future__ import annotations

# Gemstone exchange rates (NPC buy = npc_sell × 2.4).
STATIC_AVG_PRICES: dict[int, float] = {
    2130: 1200,  # Gemstone D
    2131: 3600,  # Gemstone C
    2132: 12000,  # Gemstone B
    2133: 36000,  # Gemstone A
}


def static_avg_price(external_id: int) -> float | None:
    return STATIC_AVG_PRICES.get(external_id)


def resolve_avg_price(external_id: int, market_avg: float | None) -> float | None:
    static = static_avg_price(external_id)
    if static is not None:
        return static
    return market_avg
