"""Unified market-name lexicon: token → parameter kind.

Built from craft-catalog constants plus optional encyclopedia rows. Structural
markers (+N, Sealed) are handled first; remaining suffixes are matched
longest-first against the lexicon.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.name_matching import (
    ENCHANT_PREFIX_RE,
    SA_MODIFIERS,
    clean_display_name,
    normalize_product_name,
)

# B-grade unseal class suffixes (no dash) — same as craft_catalog.item_variants.
ARMOR_CLASS_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("Heavy Armor", "heavy"),
    ("Light Armor", "light"),
    ("Robe", "magic"),
)

# Weapon rarity labels commonly stored on encyclopedia item_modifiers.rarity.
WEAPON_RARITY_LABELS: tuple[str, ...] = (
    "Lightning",
    "Thunder",
    "Hail",
    "Destruction",
    "Earth",
    "Great Gale",
    "Confusion",
    "Cleverness",
    "Concentration",
    "Holy Spirit",
    "Landslide",
    "Clairvoyance",
    "Wisdom",
    "Nature",
)

# Catalog noise that must never be stripped as a soul ability.
IGNORE_TOKENS: frozenset[str] = frozenset({"of peril"})


@dataclass(frozen=True)
class LexiconEntry:
    kind: str  # soul_crystal | rarity | armor_class
    canonical: str
    value: str | None = None  # for armor_class: heavy/light/magic


@dataclass
class VariantLexicon:
    """Longest-first token index keyed by lowercased label."""

    by_label: dict[str, LexiconEntry] = field(default_factory=dict)

    def add(self, label: str, entry: LexiconEntry) -> None:
        key = label.strip().lower()
        if not key or key in IGNORE_TOKENS:
            return
        existing = self.by_label.get(key)
        if existing is None or len(label) > len(existing.canonical):
            self.by_label[key] = entry

    def labels_by_len(self) -> list[str]:
        return sorted(self.by_label.keys(), key=len, reverse=True)


@dataclass(frozen=True)
class ParsedMarketAttrs:
    enchant_level: int | None
    soul_crystal: str | None
    rarity: str | None
    armor_class: str | None
    sealed: bool
    base_name: str
    base_normalized: str
    full_normalized: str
    # Name used for exact/full match attempts (enchant stripped, sealed kept if present).
    match_name: str


def static_lexicon() -> VariantLexicon:
    lex = VariantLexicon()
    for sa in SA_MODIFIERS:
        lex.add(sa, LexiconEntry(kind="soul_crystal", canonical=sa))
    for label in WEAPON_RARITY_LABELS:
        lex.add(label, LexiconEntry(kind="rarity", canonical=label))
    for label, code in ARMOR_CLASS_SUFFIXES:
        lex.add(label, LexiconEntry(kind="armor_class", canonical=label, value=code))
    return lex


_STATIC: VariantLexicon | None = None


def get_static_lexicon() -> VariantLexicon:
    global _STATIC
    if _STATIC is None:
        _STATIC = static_lexicon()
    return _STATIC


def build_lexicon_from_encyclopedia(rows: list) -> VariantLexicon:
    """Merge static tokens with soul/rarity names seen in encyclopedia payloads."""
    lex = static_lexicon()
    for row in rows:
        payload = getattr(row, "payload", None) or {}
        if not isinstance(payload, dict):
            continue
        modifiers = payload.get("item_modifiers") or {}
        for entry in modifiers.get("soul_crystals") or []:
            if isinstance(entry, dict) and str(entry.get("name", "")).strip():
                name = str(entry["name"]).strip()
                lex.add(name, LexiconEntry(kind="soul_crystal", canonical=name))
        for entry in modifiers.get("rarity") or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            # Skip synthetic armor Masterwork labels — not present in market names.
            if not name or name.lower().startswith("masterwork"):
                continue
            if " - " in (entry.get("full_name") or "") or name in WEAPON_RARITY_LABELS:
                lex.add(name, LexiconEntry(kind="rarity", canonical=name))
            sa = str(entry.get("sa", "")).strip()
            if sa:
                lex.add(sa, LexiconEntry(kind="soul_crystal", canonical=sa))
    return lex


def _strip_trailing_token(
    text: str, lex: VariantLexicon, *, kinds: set[str]
) -> tuple[str, LexiconEntry | None]:
    lowered = text.lower()
    for label in lex.labels_by_len():
        entry = lex.by_label[label]
        if entry.kind not in kinds:
            continue
        suffix = f" {label}"
        if lowered.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)].strip(), entry
    return text, None


def classify_market_name(
    name: str, lexicon: VariantLexicon | None = None
) -> ParsedMarketAttrs:
    """Split a market item name into typed variant attributes + base."""
    lex = lexicon or get_static_lexicon()
    cleaned = clean_display_name(name)

    enchant_level: int | None = None
    match = ENCHANT_PREFIX_RE.match(cleaned)
    if match:
        enchant_level = int(match.group(1))
        cleaned = cleaned[match.end() :].strip()

    match_name = cleaned  # enchant-stripped, sealed prefix still present if any

    sealed = False
    if cleaned.lower().startswith("sealed "):
        sealed = True
        cleaned = cleaned[7:].strip()

    soul_crystal: str | None = None
    rarity: str | None = None
    armor_class: str | None = None

    if " - " in cleaned:
        # Weapon-style: Base - Rarity [SA]
        base_part, rest = cleaned.split(" - ", 1)
        rest = rest.strip()
        rest_base, sa_entry = _strip_trailing_token(rest, lex, kinds={"soul_crystal"})
        if sa_entry is not None:
            soul_crystal = sa_entry.canonical
            rest = rest_base
        # Remaining after SA is rarity label (trust dash split).
        rarity = rest.strip() or None
        # Canonicalize rarity via lexicon when known.
        if rarity:
            entry = lex.by_label.get(rarity.lower())
            if entry and entry.kind == "rarity":
                rarity = entry.canonical
        base = base_part.strip()
    else:
        # Armor unseal suffixes first (longer labels before Robe).
        base, armor_entry = _strip_trailing_token(
            cleaned, lex, kinds={"armor_class"}
        )
        if armor_entry is not None:
            armor_class = armor_entry.value or armor_entry.canonical
            # Robe is ambiguous (whole pieces like "Avadon Robe"). Keep only when
            # the remainder still has a piece word / multi-token family name.
            if armor_entry.canonical == "Robe" and len(base.split()) < 2:
                armor_class = None
                base = cleaned
        else:
            base, sa_entry = _strip_trailing_token(
                cleaned, lex, kinds={"soul_crystal"}
            )
            if sa_entry is not None:
                soul_crystal = sa_entry.canonical

    # Rebuild sealed base for matching when sealed prefix was present.
    if sealed:
        base_for_norm = base
        # Matching sealed catalog entries uses "Sealed " + base when looking up
        # the sealed form; base_normalized drops Sealed for unseal folding.
        display_base = base
    else:
        display_base = base
        base_for_norm = base

    return ParsedMarketAttrs(
        enchant_level=enchant_level,
        soul_crystal=soul_crystal,
        rarity=rarity,
        armor_class=armor_class,
        sealed=sealed,
        base_name=display_base,
        base_normalized=normalize_product_name(base_for_norm),
        full_normalized=normalize_product_name(match_name),
        match_name=match_name,
    )
