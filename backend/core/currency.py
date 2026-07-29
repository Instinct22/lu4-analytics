"""Shared currency normalization for market ingest and analytics."""

ADENA_ALIASES = {"adena", "ad", "адена"}
MASTER_COIN_ALIASES = {"master_coin", "mastercoin", "mc", "мастер коин", "мастеркоин"}


def normalize_currency(value: str | None) -> str:
    raw = (value or "adena").strip().lower().replace(" ", "_")
    if raw in ADENA_ALIASES:
        return "adena"
    if raw in MASTER_COIN_ALIASES:
        return "master_coin"
    return raw or "adena"
