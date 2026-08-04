import html
import re
import unicodedata


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
