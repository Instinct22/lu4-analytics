from fastapi import APIRouter, Depends

from api.deps import DbSession, require_api_scope
from calculations.price_stats import recalculate_item_statistics
from schemas.market_scan import ScanBatchRequest, ScanBatchResponse, ScanRecord, ScanResponse
from services.market_scan_service import save_scan_batch, save_scan_record

router = APIRouter()


@router.post("", response_model=ScanResponse, dependencies=[Depends(require_api_scope("market_scan"))])
def scan_record(body: ScanRecord, db: DbSession):
    market_record, matched = save_scan_record(db, body)
    db.commit()

    if market_record.entity_id:
        recalculate_item_statistics(db, market_record.entity_id)
        db.commit()

    return ScanResponse(id=market_record.id, matched=matched)


@router.post("/batch", response_model=ScanBatchResponse, dependencies=[Depends(require_api_scope("market_scan"))])
def scan_batch(body: ScanBatchRequest, db: DbSession):
    saved_count, matched_count, affected_entities = save_scan_batch(db, body.records)
    db.commit()

    for entity_id in affected_entities:
        recalculate_item_statistics(db, entity_id)
    db.commit()

    return ScanBatchResponse(saved_count=saved_count, matched_count=matched_count)
