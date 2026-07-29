"""Explode the character dataset into races, classes and skills."""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy import delete
from sqlalchemy.orm import Session

from models.character import CharacterClass, CharacterRace, CharacterSkill
from services.dataset_import import register_normalizer, upsert_blob

#: Small companion blob so the races endpoint can report dataset provenance
#: without keeping the 20 MB character payload around.
META_KEY = "character_meta"


def _walk_tree(node: dict) -> Iterator[dict]:
    yield node
    for child in node.get("children") or []:
        if isinstance(child, dict):
            yield from _walk_tree(child)


def _race_by_class(races: list) -> dict[int, str]:
    """Map class id -> race id by walking each race's class tree."""
    mapping: dict[int, str] = {}
    for race in races:
        race_id = race.get("id")
        if not race_id:
            continue
        for branch in race.get("branches") or []:
            root = branch.get("root") if isinstance(branch, dict) else None
            if not isinstance(root, dict):
                continue
            for node in _walk_tree(root):
                class_id = node.get("id")
                if isinstance(class_id, int):
                    mapping.setdefault(class_id, race_id)
    return mapping


@register_normalizer("character")
def normalize_character(db: Session, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    races = [r for r in (payload.get("races") or []) if isinstance(r, dict) and r.get("id")]
    race_of_class = _race_by_class(races)

    # Full replace: the dataset is the single source of truth and small enough
    # to rewrite, which keeps the normalizer free of diffing logic.
    db.execute(delete(CharacterClass))
    db.execute(delete(CharacterSkill))
    db.execute(delete(CharacterRace))
    db.flush()

    for order, race in enumerate(races):
        db.add(
            CharacterRace(
                id=race["id"],
                name=race.get("name") or race["id"],
                sort_order=order,
                payload={"branches": race.get("branches") or []},
            )
        )
    db.flush()

    for raw_id, cls in (payload.get("classes") or {}).items():
        if not isinstance(cls, dict):
            continue
        class_id = cls.get("id") if isinstance(cls.get("id"), int) else int(raw_id)
        db.add(
            CharacterClass(
                id=class_id,
                name=cls.get("name") or str(class_id),
                slug=cls.get("slug") or "",
                icon=cls.get("icon") or "",
                portrait=cls.get("portrait") or "",
                race_id=race_of_class.get(class_id),
                payload={
                    "levels": cls.get("levels") or [],
                    "skills_by_level": cls.get("skills_by_level") or {},
                    "skills_up_to_level": cls.get("skills_up_to_level") or {},
                },
            )
        )

    for raw_id, skill in (payload.get("skills") or {}).items():
        if not isinstance(skill, dict):
            continue
        skill_id = skill.get("id") if isinstance(skill.get("id"), int) else int(raw_id)
        db.add(
            CharacterSkill(
                id=skill_id,
                name=skill.get("name") or str(skill_id),
                icon=skill.get("icon") or "",
                type=skill.get("type") or "",
                payload={
                    "levels": skill.get("levels") or {},
                    "available_for": skill.get("available_for") or [],
                },
            )
        )

    upsert_blob(
        db,
        META_KEY,
        {
            "generated_at": payload.get("generated_at"),
            "wiki_base": payload.get("wiki_base"),
        },
        None,
    )
