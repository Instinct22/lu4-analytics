import html
import re
import unicodedata
from dataclasses import dataclass


WIKI_PREFIX_RE = re.compile(
    r"^(Lu4 Wiki:\s*(Item|NPC|Skill|Quest|Location|Class|Set|Posts)\s*)",
    re.IGNORECASE,
)
RECIPE_PREFIX_RE = re.compile(r"^recipe:\s*", re.IGNORECASE)
PERCENT_100_RE = re.compile(r"\s*\(\s*100%\s*\)", re.IGNORECASE)
LEVEL_RANGE_RE = re.compile(r"\s+\d+\s*-\s*\d+\s*$")
LEVEL_PLUS_RE = re.compile(r"\s+\d+\+\s*$")
# (D-Grade), (D), (No-Grade), (No Grade)
GRADE_PAREN_RE = re.compile(
    r"\(\s*(NG|No(?:\s*-?\s*Grade)?|D|C|B|A|S)(?:\s*-?\s*Grade)?\s*\)",
    re.IGNORECASE,
)
TRAILING_NG_RE = re.compile(r"\s+NG\s*$", re.IGNORECASE)
TRAILING_GRADE_LETTER_RE = re.compile(r"\s+([DCBAS])\s*$", re.IGNORECASE)
APOSTROPHE_RE = re.compile(r"[''`ʼʹ]")

# Leading enchant marker on in-game names, e.g. "+3 Conjurer's Knife Acumen".
ENCHANT_PREFIX_RE = re.compile(r"^\+(\d{1,3})\s+")

# Weapon Soul Ability suffixes that the game appends to the base item name.
# Superset of scripts/craft_catalog/item_variants.py::SA_MODIFIERS — extended
# with every soul-ability name present in the items encyclopedia so market names
# fold onto their base. Excludes garbage tokens like "of Peril" (a bad catalog
# entry) that would strip real base words.
SA_MODIFIERS: tuple[str, ...] = (
    "Critical Damage",
    "Critical Rate",
    "Critical Bleed",
    "Critical Stun",
    "Magic Paralyze",
    "Magic Weakness",
    "Magic Silence",
    "Magic Regeneration",
    "Magic Focus",
    "Magic Power",
    "Magic Poison",
    "Magic Chaos",
    "Magic Hold",
    "Mental Shield",
    "Blessed Body",
    "Back Blow",
    "Rsk. Focus",
    "Rsk. Haste",
    "Conversion",
    "Guidance",
    "Empower",
    "Acumen",
    "Anger",
    "Cheap Shot",
    "Quick Recovery",
    "Towering Blow",
    "Wide Blow",
    "Wild Blow",
    "Mana Up",
    "M. Atk.",
    "Health",
    "Focus",
    "Haste",
    "Evasion",
)
# Longest-first so "Magic Focus" wins over "Focus", "Rsk. Haste" over "Haste".
_SA_MODIFIERS_BY_LEN: tuple[str, ...] = tuple(sorted(SA_MODIFIERS, key=len, reverse=True))


@dataclass(frozen=True)
class ParsedMarketName:
    """Structured breakdown of a raw in-game market item name."""

    enchant_level: int | None
    soul_crystal: str | None
    rarity: str | None
    base_name: str
    base_normalized: str
    full_normalized: str
    armor_class: str | None = None
    sealed: bool = False


def _split_soul_ability(text: str) -> tuple[str, str | None]:
    """Strip a trailing soul-ability suffix. Returns (base, soul_crystal)."""
    lowered = text.lower()
    for modifier in _SA_MODIFIERS_BY_LEN:
        suffix = f" {modifier.lower()}"
        if lowered.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)].strip(), modifier
    return text, None


def parse_market_name(name: str) -> ParsedMarketName:
    """Split a market item name into typed attrs via the unified lexicon."""
    from services.variant_lexicon import classify_market_name

    attrs = classify_market_name(name)
    return ParsedMarketName(
        enchant_level=attrs.enchant_level,
        soul_crystal=attrs.soul_crystal,
        rarity=attrs.rarity,
        armor_class=attrs.armor_class,
        sealed=attrs.sealed,
        base_name=attrs.base_name,
        base_normalized=attrs.base_normalized,
        full_normalized=attrs.full_normalized,
    )


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-") or "item"


def unescape_text(value: str | None) -> str:
    """Decode HTML entities stored in wiki/import names (e.g. &#039; → ')."""
    if not value:
        return ""
    return html.unescape(value)


def clean_display_name(name: str) -> str:
    cleaned = WIKI_PREFIX_RE.sub("", name or "").strip()
    cleaned = unescape_text(cleaned)
    return cleaned or unescape_text(name)


def is_recipe_name(name: str) -> bool:
    """True when the display/raw name denotes a recipe scroll, not its product."""
    return bool(RECIPE_PREFIX_RE.match(clean_display_name(name)))


def _canonical_grade_token(raw: str) -> str:
    token = re.sub(r"[\s-]+", "", raw or "").upper()
    if token in {"NG", "NO", "NOGRADE"}:
        return "(no-grade)"
    if token in {"D", "C", "B", "A", "S"}:
        return f"({token.lower()}-grade)"
    return f"({raw.strip().lower()})"


def normalize_product_name(name: str) -> str:
    """Normalize for market matching.

    Keeps the ``Recipe:`` prefix so recipe scrolls stay distinct from the
    crafted product. Unifies grade spellings (``D`` / ``(D)`` / ``(D-Grade)``),
    drops apostrophes, optional ``(100%)`` and level ranges like ``20-39``.
    """
    value = clean_display_name(name)
    value = PERCENT_100_RE.sub("", value)
    value = LEVEL_RANGE_RE.sub("", value)
    value = LEVEL_PLUS_RE.sub("", value)
    value = GRADE_PAREN_RE.sub(lambda m: _canonical_grade_token(m.group(1)), value)
    # Trailing crystal marker, not an item grade.
    value = TRAILING_NG_RE.sub("", value)

    trailing = TRAILING_GRADE_LETTER_RE.search(value)
    if trailing:
        letter = trailing.group(1).lower()
        base = value[: trailing.start()].rstrip()
        grade = f"({letter}-grade)"
        if not base.lower().endswith(grade):
            value = f"{base} {grade}"
        else:
            value = base

    value = APOSTROPHE_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value
