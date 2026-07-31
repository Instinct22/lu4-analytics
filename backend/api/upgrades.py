from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.deps import DbSession, require_permission
from models.analytics import AnalyticsDataset

router = APIRouter()

DATASET_KEY = "weapon_upgrades"


@router.get("/catalog", dependencies=[Depends(require_permission("nav.craft"))])
def get_catalog(db: DbSession):
    dataset = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == DATASET_KEY))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Weapon upgrades catalog not loaded")
    return {
        "generated_at": dataset.generated_at.isoformat() if dataset.generated_at else None,
        **(dataset.payload if isinstance(dataset.payload, dict) else {}),
    }
