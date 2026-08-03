import html
import re
import unicodedata


WIKI_PREFIX_RE = re.compile(
    r"^(Lu4 Wiki:\s*(Item|NPC|Skill|Quest|Location|Class|Set|Posts)\s*)",
    re.IGNORECASE,
)
GRADE_SUFFIX_RE = re.compile(r"\s+(NG|D|C|B|A|S)\s*$", re.IGNORECASE)
RECIPE_PREFIX_RE = re.compile(r"^recipe:\s*", re.IGNORECASE)


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


def normalize_product_name(name: str) -> str:
    value = clean_display_name(name)
    value = RECIPE_PREFIX_RE.sub("", value)
    value = GRADE_SUFFIX_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value
