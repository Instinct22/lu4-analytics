from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession, verify_api_key
from schemas.import_ import ImportLogResponse, ImportRequest, ImportResponse
from services import import_service

router = APIRouter()


@router.post("", response_model=ImportResponse, dependencies=[Depends(verify_api_key)])
def import_records(body: ImportRequest, db: DbSession):
    return import_service.import_price_records(db, body)


@router.get("/logs", response_model=list[ImportLogResponse])
def import_logs(db: DbSession, user: CurrentUser, limit: int = 50):
    return import_service.list_import_logs(db, limit)
