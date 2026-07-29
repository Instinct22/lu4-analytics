"""Merge gear item variants (rare, SA, PvP, weapon SA, sealed) into canonical entries."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from craft_catalog.item_classify import armor_variant_type

SA_MODIFIERS: tuple[str, ...] = (
    "Critical Damage",
    "Critical Rate",
    "Magic Paralyze",
    "Magic Weakness",
    "Magic Silence",
    "Magic Focus",
    "Magic Power",
    "M. Atk.",
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
    "Critical Stun",
    "Wide Blow",
    "Health",
    "Focus",
    "Haste",
    "Evasion",
)

_PASSIVE_RE = re.compile(r"<Passive Effect>\s*([^<]+)", re.I)
_RARE_EFFECT_RE = re.compile(r"<Rare Item Effect>\s*([^<]+)", re.I)
_NUMERIC_NAME_RE = re.compile(r"^\d+$")
_PLACEHOLDER_NAME_RE = re.compile(r"^#\d+$", re.I)
_SOUL_CRYSTAL_MARKER = "<Available Soul Crystals>"

# Unsealing a B-grade armour piece yields one of three armour classes; higher
# grades yield a single piece named after the same suffix pattern.
UNSEAL_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("Heavy Armor", "heavy"),
    ("Light Armor", "light"),
    ("Robe", "magic"),
)

# Trailing words that describe the armour piece rather than its set family.
_ARMOR_PIECE_WORDS = frozenset(
    {
        "armor",
        "armour",
        "mail",
        "breastplate",
        "gaiters",
        "gauntlets",
        "gloves",
        "boots",
        "shield",
        "helmet",
        "circlet",
        "robe",
        "leggings",
        "stockings",
        "tunic",
        "leather",
        "plate",
        "shirt",
        "buckler",
        "mask",
        "hat",
        "cap",
    }
)


def _strip_pvp(name: str) -> tuple[str, bool]:
    if " {PvP}" in name:
        return name.replace(" {PvP}", "").strip(), True
    return name, False


def _parse_sa_suffix(name: str) -> tuple[str, str | None]:
    for mod in SA_MODIFIERS:
        suffix = f" {mod}"
        if name.endswith(suffix):
            return name[: -len(suffix)].strip(), mod
    return name, None


def classify_item_name(name: str) -> dict[str, Any]:
    raw = (name or "").strip()
    if not raw:
        return {"kind": "exclude", "reason": "empty_name"}

    if _NUMERIC_NAME_RE.fullmatch(raw) or _PLACEHOLDER_NAME_RE.fullmatch(raw):
        return {"kind": "exclude", "reason": "placeholder_name"}

    if raw.lower().startswith("the 1st") or raw.lower().startswith("the 1ts"):
        return {"kind": "exclude", "reason": "the_1st"}

    cleaned, is_pvp = _strip_pvp(raw)

    if " - " in cleaned:
        base_name, rest = cleaned.split(" - ", 1)
        rare_label, sa = _parse_sa_suffix(rest.strip())
        return {
            "kind": "variant",
            "variant_type": "rare_sa" if sa else "rare",
            "base_name": base_name.strip(),
            "rare": rare_label.strip(),
            "sa": sa,
            "pvp": is_pvp,
        }

    base_name, sa = _parse_sa_suffix(cleaned)
    if sa:
        return {
            "kind": "variant",
            "variant_type": "sa",
            "base_name": base_name,
            "sa": sa,
            "pvp": is_pvp,
        }

    if is_pvp:
        return {
            "kind": "variant",
            "variant_type": "pvp",
            "base_name": cleaned,
            "pvp": True,
        }

    return {"kind": "base", "base_name": cleaned}


def _extract_effect(description: str | None, pattern: re.Pattern[str]) -> str | None:
    if not description:
        return None
    match = pattern.search(description)
    if not match:
        return None
    text = match.group(1).strip()
    return text or None


def _has_rare_effect(item: dict[str, Any]) -> bool:
    desc = item.get("description") or item.get("effects") or ""
    if "<Rare Item Effect>" in desc:
        return True
    if "Sealed Masterwork Item" in desc:
        return True
    if "Masterwork Item" in desc and item.get("name", "").startswith("Sealed "):
        return True
    return False


def _is_fishing_rod(item: dict[str, Any]) -> bool:
    return "fishing rod" in (item.get("type") or "").lower()


def _is_placeholder(item: dict[str, Any]) -> bool:
    name = (item.get("name") or "").strip()
    if _PLACEHOLDER_NAME_RE.fullmatch(name):
        return True
    if name.startswith("#") and not (item.get("type") or "").strip():
        return True
    return False


def _parse_soul_crystals_from_description(description: str | None) -> list[dict[str, Any]]:
    if not description:
        return []
    idx = description.find(_SOUL_CRYSTAL_MARKER)
    if idx < 0:
        return []
    tail = description[idx + len(_SOUL_CRYSTAL_MARKER) :].strip()
    if "<" in tail:
        tail = tail.split("<", 1)[0].strip()

    names = sorted({*SA_MODIFIERS, "Health", "Focus", "Haste", "Critical Damage"}, key=len, reverse=True)
    pattern = re.compile(r"(" + "|".join(re.escape(n) for n in names) + r"):\s*", re.I)
    matches = list(pattern.finditer(tail))
    if not matches:
        return []

    entries: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(tail)
        effect = tail[start:end].strip().strip(".")
        if not effect:
            continue
        entry: dict[str, Any] = {"name": name.strip(), "effect": effect}
        if "pvp" in effect.lower():
            entry["pvp"] = True
        entries.append(entry)
    return entries


def _parse_unseal_suffix(name: str) -> tuple[str, str, str] | None:
    """`Zubei's Gauntlets Heavy Armor` -> (base, suffix label, armour class)."""
    raw = (name or "").strip()
    if not raw or raw.startswith("Sealed "):
        return None
    for suffix, armor_class in UNSEAL_SUFFIXES:
        if not raw.endswith(f" {suffix}"):
            continue
        base = raw[: -len(suffix)].strip()
        if not base:
            return None
        return base, suffix, armor_class
    return None


def _armor_family(name: str) -> str:
    """Strip trailing piece words: `Avadon Leather Mail` -> `Avadon`."""
    words = (name or "").strip().split()
    while len(words) > 1 and words[-1].lower().strip(".,") in _ARMOR_PIECE_WORDS:
        words.pop()
    return " ".join(words)


def _resolve_armor_sibling(
    variant: dict[str, Any],
    base_name: str,
    items: dict[int, dict[str, Any]],
    gear_ids: list[int],
) -> int | None:
    """Match an armour variant to its base by set family + slot + grade."""
    v_type = (variant.get("type") or "").strip().lower()
    if not v_type.startswith("armor"):
        return None
    family = _armor_family(base_name).lower()
    if not family:
        return None
    v_grade = (variant.get("grade") or "").strip().upper()

    for iid in gear_ids:
        item = items[iid]
        if item.get("section") != "gear":
            continue
        if (item.get("type") or "").strip().lower() != v_type:
            continue
        if (item.get("grade") or "").strip().upper() != v_grade:
            continue
        if classify_item_name(item.get("name") or "").get("kind") != "base":
            continue
        if _armor_family(item.get("name") or "").lower() != family:
            continue
        return iid
    return None


def _resolve_base_id(
    variant: dict[str, Any],
    classification: dict[str, Any],
    by_name: dict[str, list[int]],
    items: dict[int, dict[str, Any]],
) -> int | None:
    base_name = classification.get("base_name") or ""
    candidates = list(by_name.get(base_name.lower(), []))
    if not candidates:
        return None

    v_type = (variant.get("type") or "").strip().lower()
    v_grade = (variant.get("grade") or "").strip().upper()

    typed = [cid for cid in candidates if (items[cid].get("type") or "").strip().lower() == v_type]
    if typed:
        candidates = typed

    graded = [cid for cid in candidates if (items[cid].get("grade") or "").strip().upper() == v_grade]
    if graded:
        candidates = graded

    for cid in candidates:
        base_cls = classify_item_name(items[cid].get("name") or "")
        if base_cls.get("kind") == "base":
            return cid

    return candidates[0] if candidates else None


def _craftable_ids(craft_by_product: dict[str, Any] | None) -> set[int]:
    out: set[int] = set()
    for raw in (craft_by_product or {}):
        try:
            out.add(int(raw))
        except (TypeError, ValueError):
            pass
    return out


def _weapon_base_names(craftable_ids: set[int], items: dict[int, dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for iid in craftable_ids:
        item = items.get(iid)
        if not item:
            continue
        if not (item.get("type") or "").lower().startswith("weapon"):
            continue
        name = (item.get("name") or "").strip()
        if name:
            names.add(name)
    return sorted(names, key=len, reverse=True)


def _match_weapon_sa(name: str, weapon_bases: list[str]) -> tuple[str, str] | None:
    for base in weapon_bases:
        prefix = f"{base} "
        if name.startswith(prefix):
            suffix = name[len(prefix) :].strip()
            if suffix and classify_item_name(name).get("kind") == "base":
                return base, suffix
    return None


def _pick_canonical(ids: list[int], items: dict[int, dict[str, Any]], craftable_ids: set[int]) -> int:
    def score(iid: int) -> tuple[int, int]:
        item = items[iid]
        points = 0
        if iid in craftable_ids:
            points += 100
        if not _has_rare_effect(item):
            points += 50
        if (item.get("craft") or {}).get("craftable"):
            points += 25
        return (points, -iid)

    return max(ids, key=score)


# Exclusions produced by this module; anything else came from an earlier stage
# and must survive a re-run untouched.
OWNED_EXCLUDE_REASONS = frozenset(
    {
        "empty_name",
        "placeholder_name",
        "the_1st",
        "variant",
        "duplicate_variant",
        "unseal_variant",
        "unsealed_variant",
        "weapon_sa_variant",
        "rare_orphan",
        "rare_sa_orphan",
        "pvp_orphan",
    }
)


def _reset_variant_state(typed_items: dict[int, dict[str, Any]]) -> None:
    """Undo a previous merge so the pipeline stays idempotent across re-runs."""
    for item in typed_items.values():
        item.pop("item_modifiers", None)
        item.pop("unseal_variants", None)
        if item.get("exclude_reason") in OWNED_EXCLUDE_REASONS:
            item["section"] = item.pop("variant_prev_section", None) or "gear"
            item.pop("exclude_reason", None)
            item.pop("variant_of", None)
            item.pop("variant_kind", None)
        else:
            item.pop("variant_prev_section", None)


def _exclude_item(item: dict[str, Any], reason: str, *, base_id: int | None = None, kind: str | None = None) -> None:
    if item.get("section") != "excluded":
        item["variant_prev_section"] = item.get("section") or "gear"
    item["section"] = "excluded"
    item["exclude_reason"] = reason
    if base_id is not None:
        item["variant_of"] = base_id
    if kind:
        item["variant_kind"] = kind


_UNINFORMATIVE_RARE_EFFECTS = frozenset({"", "sealed masterwork item", "masterwork item"})


def _rarity_label(item: dict[str, Any]) -> str:
    """Rare bonuses differ per unsealed armour class, so name them accordingly."""
    parsed = _parse_unseal_suffix(item.get("name") or "")
    if parsed:
        return f"Masterwork ({parsed[1]})"
    return "Masterwork"


def _append_rarity(bucket: dict[str, Any], item: dict[str, Any], iid: int, *, label: str | None = None) -> None:
    desc = item.get("description") or item.get("effects") or ""
    effect = _extract_effect(desc, _RARE_EFFECT_RE)
    if not effect and "Masterwork" in desc:
        effect = desc.split(".", 1)[0].strip() if desc else None
    entry = {
        "name": label or _rarity_label(item),
        "full_name": item.get("name"),
        "id": iid,
        "effect": effect,
    }
    bucket["rarity"].append(entry)


def _dedupe_modifier_entries(entries: list[dict[str, Any]], *, drop_empty: bool) -> list[dict[str, Any]]:
    pool = entries
    if drop_empty:
        informative = [
            e for e in entries if (e.get("effect") or "").strip().lower() not in _UNINFORMATIVE_RARE_EFFECTS
        ]
        pool = informative or entries[:1]

    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for entry in pool:
        sig = (entry.get("name"), (entry.get("effect") or "").strip(), entry.get("sa"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(entry)
    return out


def _append_weapon_sa(bucket: dict[str, Any], item: dict[str, Any], iid: int, sa_name: str) -> None:
    desc = item.get("description") or item.get("effects") or ""
    effect = _extract_effect(desc, _PASSIVE_RE) or desc or None
    bucket["soul_crystals"].append(
        {
            "name": sa_name,
            "full_name": item.get("name"),
            "id": iid,
            "effect": effect,
            "applied": True,
            "weapon_sa": True,
        }
    )


def _merge_duplicate_names(
    gear_ids: list[int],
    typed_items: dict[int, dict[str, Any]],
    modifiers: dict[int, dict[str, Any]],
    craftable_ids: set[int],
) -> None:
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for iid in gear_ids:
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        cls = classify_item_name(item.get("name") or "")
        if cls.get("kind") != "base":
            continue
        key = (
            (item.get("name") or "").strip().lower(),
            (item.get("type") or "").strip().lower(),
            (item.get("grade") or "").strip().upper(),
        )
        groups[key].append(iid)

    for ids in groups.values():
        if len(ids) < 2:
            continue
        canonical = _pick_canonical(ids, typed_items, craftable_ids)
        bucket = modifiers.setdefault(canonical, {"rarity": [], "soul_crystals": [], "pvp": None})
        for iid in ids:
            if iid == canonical:
                continue
            item = typed_items[iid]
            _exclude_item(item, "duplicate_variant", base_id=canonical, kind="rare")
            _append_rarity(bucket, item, iid)


def _resolve_unseal_target(
    base_name: str,
    variant: dict[str, Any],
    name_index: dict[str, list[int]],
    items: dict[int, dict[str, Any]],
    craftable_ids: set[int],
) -> int | None:
    """Sealed piece is the catalog entry; fall back to an unsuffixed base piece."""
    sealed = [
        iid
        for iid in name_index.get(f"sealed {base_name}".lower(), [])
        if items[iid].get("section") == "gear"
    ]
    if sealed:
        sealed.sort(key=lambda iid: (iid not in craftable_ids, iid))
        return sealed[0]

    v_grade = (variant.get("grade") or "").strip().upper()
    plain = [
        iid
        for iid in name_index.get(base_name.lower(), [])
        if items[iid].get("section") == "gear"
        and (items[iid].get("grade") or "").strip().upper() == v_grade
    ]
    if plain:
        plain.sort(key=lambda iid: (iid not in craftable_ids, iid))
        return plain[0]
    return None


def _merge_unseal_variants(
    gear_ids: list[int],
    typed_items: dict[int, dict[str, Any]],
    name_index: dict[str, list[int]],
    craftable_ids: set[int],
) -> None:
    """Hide unsealed armour pieces, listing them on the sealed catalog entry."""
    for iid in list(gear_ids):
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        parsed = _parse_unseal_suffix(item.get("name") or "")
        if not parsed:
            continue
        base_name, suffix, armor_class = parsed
        target_id = _resolve_unseal_target(base_name, item, name_index, typed_items, craftable_ids)
        if target_id is None or target_id == iid:
            continue

        _exclude_item(item, "unseal_variant", base_id=target_id, kind="unseal")
        target = typed_items[target_id]
        variants = target.setdefault("unseal_variants", [])
        if any(v.get("id") == iid for v in variants):
            continue
        variants.append(
            {
                "id": iid,
                "name": item.get("name"),
                "label": suffix,
                "armor_class": armor_class,
                "grade": item.get("grade"),
                "stats": item.get("stats"),
            }
        )


def _empty_bucket() -> dict[str, Any]:
    return {"rarity": [], "soul_crystals": [], "pvp": None}


def _terminal_visible(iid: int, typed_items: dict[int, dict[str, Any]]) -> int | None:
    """Follow variant_of links until a non-excluded item is reached."""
    seen: set[int] = set()
    current: int | None = iid
    while current is not None and current not in seen:
        seen.add(current)
        item = typed_items.get(current)
        if item is None:
            return None
        if item.get("section") != "excluded":
            return current
        nxt = item.get("variant_of")
        current = nxt if isinstance(nxt, int) else None
    return None


def _merge_modifier_buckets(
    target: dict[str, Any],
    source: dict[str, Any],
) -> None:
    for key in ("rarity", "soul_crystals"):
        seen = {(e.get("name"), e.get("full_name")) for e in target.get(key, [])}
        for entry in source.get(key, []):
            sig = (entry.get("name"), entry.get("full_name"))
            if sig in seen:
                continue
            target.setdefault(key, []).append(entry)
            seen.add(sig)
    if source.get("pvp") and not target.get("pvp"):
        target["pvp"] = source["pvp"]


def _apply_sealed_catalog_rules(
    typed_items: dict[int, dict[str, Any]],
    gear_ids: list[int],
    modifiers: dict[int, dict[str, Any]],
) -> None:
    for iid in list(gear_ids):
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        name = item.get("name") or ""
        if name.startswith("Sealed "):
            continue
        group = item.get("sealed_group")
        if not isinstance(group, dict):
            continue
        sealed_id = group.get("sealed_id")
        if not sealed_id or sealed_id == iid:
            continue
        # The recorded sealed id may itself be a merged duplicate.
        sealed_id = _terminal_visible(sealed_id, typed_items) or sealed_id
        if sealed_id == iid:
            continue

        if sealed_id in typed_items:
            dst = typed_items[sealed_id]
            src_mod = item.get("item_modifiers") or modifiers.get(iid)
            if src_mod:
                bucket = modifiers.setdefault(
                    sealed_id,
                    dst.get("item_modifiers") or {"rarity": [], "soul_crystals": [], "pvp": None},
                )
                _merge_modifier_buckets(bucket, src_mod)
                if bucket["rarity"] or bucket["soul_crystals"] or bucket["pvp"]:
                    dst["item_modifiers"] = bucket

            moved = item.pop("unseal_variants", None)
            if moved:
                dst_variants = dst.setdefault("unseal_variants", [])
                known = {v.get("id") for v in dst_variants}
                dst_variants.extend(v for v in moved if v.get("id") not in known)

            # The unsealed piece is itself an unseal result of the sealed entry.
            dst_variants = dst.setdefault("unseal_variants", [])
            if not any(v.get("id") == iid for v in dst_variants):
                dst_variants.append(
                    {
                        "id": iid,
                        "name": item.get("name"),
                        "label": None,
                        "armor_class": armor_variant_type(item.get("type") or ""),
                        "grade": item.get("grade"),
                        "stats": item.get("stats"),
                    }
                )

        _exclude_item(item, "unsealed_variant", base_id=sealed_id)


def _rehome_excluded_modifiers(
    typed_items: dict[int, dict[str, Any]],
    modifiers: dict[int, dict[str, Any]],
) -> None:
    """Re-point variant links and modifiers that landed on a merged-away item."""
    for iid, item in typed_items.items():
        if item.get("section") != "excluded":
            continue
        parent = item.get("variant_of")
        if not isinstance(parent, int):
            continue
        resolved = _terminal_visible(parent, typed_items)
        if resolved is not None and resolved != parent:
            item["variant_of"] = resolved

    for iid, bucket in list(modifiers.items()):
        item = typed_items.get(iid)
        if item is None or item.get("section") != "excluded":
            continue
        target = _terminal_visible(iid, typed_items)
        if target is None or target == iid:
            continue

        if bucket.get("rarity") or bucket.get("soul_crystals") or bucket.get("pvp"):
            _merge_modifier_buckets(modifiers.setdefault(target, _empty_bucket()), bucket)
            modifiers[iid] = _empty_bucket()

        stale = item.pop("item_modifiers", None)
        if stale:
            _merge_modifier_buckets(modifiers.setdefault(target, _empty_bucket()), stale)

        moved = item.pop("unseal_variants", None)
        if moved:
            dst_variants = typed_items[target].setdefault("unseal_variants", [])
            known = {v.get("id") for v in dst_variants}
            dst_variants.extend(v for v in moved if v.get("id") not in known)


def _rebuild_by_name(gear_ids: list[int], typed_items: dict[int, dict[str, Any]]) -> dict[str, list[int]]:
    by_name: dict[str, list[int]] = {}
    for iid in gear_ids:
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        cls = classify_item_name(item.get("name") or "")
        if cls.get("kind") != "base":
            continue
        by_name.setdefault(cls["base_name"].lower(), []).append(iid)
    return by_name


def merge_gear_variants(items: dict[str, Any], *, craft_by_product: dict[str, Any] | None = None) -> None:
    """Mutate encyclopedia items: hide variants, enrich bases with modifier metadata."""
    typed_items: dict[int, dict[str, Any]] = {}
    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        typed_items[iid] = item

    _reset_variant_state(typed_items)

    craftable_ids = _craftable_ids(craft_by_product)
    weapon_bases = _weapon_base_names(craftable_ids, typed_items)

    for item in typed_items.values():
        if _is_placeholder(item):
            _exclude_item(item, "placeholder_name")
            continue
        if _is_fishing_rod(item):
            item["section"] = "other"
            item["other_subcategory"] = "misc"

    gear_ids = [iid for iid, item in typed_items.items() if item.get("section") == "gear"]
    by_name = _rebuild_by_name(gear_ids, typed_items)

    modifiers: dict[int, dict[str, Any]] = {iid: {"rarity": [], "soul_crystals": [], "pvp": None} for iid in gear_ids}

    for iid in list(gear_ids):
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        cls = classify_item_name(item.get("name") or "")
        if cls.get("kind") == "exclude":
            _exclude_item(item, cls.get("reason") or "excluded")
            continue
        if cls.get("kind") != "variant":
            continue

        variant_type = cls.get("variant_type")
        base_id = _resolve_base_id(item, cls, by_name, typed_items)
        if base_id is None and variant_type in {"rare", "rare_sa", "pvp"}:
            base_id = _resolve_armor_sibling(item, cls.get("base_name") or "", typed_items, gear_ids)
        if base_id is None:
            # Rare/PvP suffixes describe a property, never a standalone item.
            if variant_type in {"rare", "rare_sa", "pvp"}:
                _exclude_item(item, f"{variant_type}_orphan", kind=variant_type)
            continue
        if base_id == iid:
            continue

        _exclude_item(item, "variant", base_id=base_id, kind=variant_type)
        bucket = modifiers.setdefault(base_id, {"rarity": [], "soul_crystals": [], "pvp": None})
        desc = item.get("description") or item.get("effects") or ""

        if cls.get("variant_type") in {"rare", "rare_sa"}:
            entry = {
                "name": cls.get("rare") or "",
                "full_name": item.get("name"),
                "id": iid,
                "effect": _extract_effect(desc, _RARE_EFFECT_RE),
            }
            if cls.get("sa"):
                entry["sa"] = cls["sa"]
                sa_effect = _extract_effect(desc, _PASSIVE_RE)
                if sa_effect:
                    entry["sa_effect"] = sa_effect
            if cls.get("pvp"):
                entry["pvp"] = True
            bucket["rarity"].append(entry)
            continue

        if cls.get("variant_type") == "sa":
            bucket["soul_crystals"].append(
                {
                    "name": cls.get("sa") or "",
                    "full_name": item.get("name"),
                    "id": iid,
                    "effect": _extract_effect(desc, _PASSIVE_RE),
                    "applied": True,
                    "pvp": bool(cls.get("pvp")),
                }
            )
            continue

        if variant_type == "pvp":
            rare_effect = _extract_effect(desc, _RARE_EFFECT_RE)
            if rare_effect:
                # A rare PvP piece carries both properties at once.
                if not any(r.get("id") == iid for r in bucket["rarity"]):
                    bucket["rarity"].append(
                        {
                            "name": "Masterwork",
                            "full_name": item.get("name"),
                            "id": iid,
                            "effect": rare_effect,
                            "pvp": True,
                        }
                    )
            if not bucket.get("pvp") or not rare_effect:
                bucket["pvp"] = {
                    "available": True,
                    "full_name": item.get("name"),
                    "id": iid,
                    "notes": (None if rare_effect else desc) or None,
                }

    for iid in list(gear_ids):
        item = typed_items[iid]
        if item.get("section") != "gear":
            continue
        match = _match_weapon_sa(item.get("name") or "", weapon_bases)
        if not match:
            continue
        base_name, sa_suffix = match
        base_candidates = [cid for cid in craftable_ids if (typed_items.get(cid) or {}).get("name") == base_name]
        if not base_candidates:
            continue
        base_id = base_candidates[0]
        if base_id == iid:
            continue
        _exclude_item(item, "weapon_sa_variant", base_id=base_id, kind="weapon_sa")
        bucket = modifiers.setdefault(base_id, {"rarity": [], "soul_crystals": [], "pvp": None})
        _append_weapon_sa(bucket, item, iid, sa_suffix)

    gear_ids = [iid for iid, item in typed_items.items() if item.get("section") == "gear"]
    _merge_duplicate_names(gear_ids, typed_items, modifiers, craftable_ids)

    gear_ids = [iid for iid, item in typed_items.items() if item.get("section") == "gear"]
    name_index: dict[str, list[int]] = {}
    for iid in gear_ids:
        key = (typed_items[iid].get("name") or "").strip().lower()
        name_index.setdefault(key, []).append(iid)
    _merge_unseal_variants(gear_ids, typed_items, name_index, craftable_ids)

    gear_ids = [iid for iid, item in typed_items.items() if item.get("section") == "gear"]
    _apply_sealed_catalog_rules(typed_items, gear_ids, modifiers)
    _rehome_excluded_modifiers(typed_items, modifiers)

    gear_ids = [iid for iid, item in typed_items.items() if item.get("section") == "gear"]
    for iid in gear_ids:
        item = typed_items[iid]
        cls = classify_item_name(item.get("name") or "")
        if cls.get("kind") != "base":
            continue

        bucket = modifiers.get(iid) or {"rarity": [], "soul_crystals": [], "pvp": None}
        existing_sa = {entry.get("name") for entry in bucket["soul_crystals"]}
        for entry in _parse_soul_crystals_from_description(item.get("description") or item.get("effects")):
            if entry["name"] in existing_sa:
                continue
            entry["applied"] = False
            bucket["soul_crystals"].append(entry)
            existing_sa.add(entry["name"])

        masterwork = item.get("masterwork")
        if isinstance(masterwork, dict):
            rare_name = masterwork.get("rareName")
            bonus = masterwork.get("bonus") or {}
            raw_bonus = bonus.get("raw") if isinstance(bonus, dict) else None
            if rare_name:
                # Only a " - <attribute>" suffix is a rarity label; a bare name is
                # just the unsealed piece and carries no rarity information.
                rare_label = rare_name.split(" - ", 1)[1] if " - " in rare_name else "Masterwork"
                if not any(r.get("name") == rare_label for r in bucket["rarity"]):
                    bucket["rarity"].append(
                        {
                            "name": rare_label,
                            "full_name": rare_name,
                            "effect": raw_bonus,
                            "from_masterwork": True,
                        }
                    )

        rarity = _dedupe_modifier_entries(bucket["rarity"], drop_empty=True)
        soul_crystals = _dedupe_modifier_entries(bucket["soul_crystals"], drop_empty=False)
        if rarity or soul_crystals or bucket["pvp"]:
            item["item_modifiers"] = {
                "rarity": rarity,
                "soul_crystals": soul_crystals,
                "pvp": bucket["pvp"],
            }
