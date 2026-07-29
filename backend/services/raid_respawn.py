"""Respawn window parsing, e.g. "6 hours ± 2 hours" -> (14400, 28800) seconds."""

from __future__ import annotations

import re

_UNIT = r"hours?|hrs?|minutes?|mins?"
_RANGE_RE = re.compile(rf"(\d+)\s*({_UNIT})\s*[±+\-]\s*(\d+)\s*({_UNIT})", re.IGNORECASE)
_SINGLE_RE = re.compile(rf"(\d+)\s*({_UNIT})", re.IGNORECASE)


def _unit_seconds(unit: str) -> int:
    return 60 if unit.lower().startswith("m") else 3600


def parse_respawn(raw: str | None) -> tuple[int, int] | None:
    """Return (min_sec, max_sec), or None for fixed and unparsable schedules."""
    if not raw:
        return None
    # Scraped sources sometimes lose the ± character to a replacement glyph.
    text = raw.replace("\ufffd", "±").strip()
    if text.lower() == "fixed":
        return None

    ranged = _RANGE_RE.search(text)
    if ranged:
        base = int(ranged.group(1)) * _unit_seconds(ranged.group(2))
        variance = int(ranged.group(3)) * _unit_seconds(ranged.group(4))
        return max(0, base - variance), base + variance

    single = _SINGLE_RE.search(text)
    if single:
        base = int(single.group(1)) * _unit_seconds(single.group(2))
        return base, base

    return None
