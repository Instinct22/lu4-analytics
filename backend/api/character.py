from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.deps import DbSession, require_permission
from models.analytics import AnalyticsDataset
from models.character import CharacterClass, CharacterRace, CharacterSkill
from services.normalizers.character import META_KEY

router = APIRouter(dependencies=[Depends(require_permission("nav.character"))])

DEFAULT_WIKI_BASE = "https://masterwork.wiki"


@router.get("/races")
def list_races(db: DbSession):
    races = db.scalars(select(CharacterRace).order_by(CharacterRace.sort_order)).all()
    meta_row = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == META_KEY))
    meta = meta_row.payload if meta_row and isinstance(meta_row.payload, dict) else {}
    return {
        "generated_at": meta.get("generated_at"),
        "wiki_base": meta.get("wiki_base") or DEFAULT_WIKI_BASE,
        "races": [
            {
                "id": race.id,
                "name": race.name,
                "branches": (race.payload or {}).get("branches") or [],
            }
            for race in races
        ],
    }


@router.get("/classes/{class_id}")
def get_class(class_id: int, db: DbSession):
    cls = db.get(CharacterClass, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    payload = cls.payload or {}
    return {
        "id": cls.id,
        "name": cls.name,
        "slug": cls.slug,
        "icon": cls.icon,
        "portrait": cls.portrait,
        "race_id": cls.race_id,
        "levels": payload.get("levels") or [],
        "skills_by_level": payload.get("skills_by_level") or {},
        "skills_up_to_level": payload.get("skills_up_to_level") or {},
    }


@router.get("/skills/{skill_id}")
def get_skill(skill_id: int, db: DbSession):
    skill = db.get(CharacterSkill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    payload = skill.payload or {}
    return {
        "id": skill.id,
        "name": skill.name,
        "icon": skill.icon,
        "type": skill.type,
        "levels": payload.get("levels") or {},
        "available_for": payload.get("available_for") or [],
    }
