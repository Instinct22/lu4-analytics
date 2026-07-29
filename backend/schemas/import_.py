import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ImportRecord(BaseModel):
    product_name: str
    seller: str
    price: Decimal
    currency: str = "RUB"
    quantity: int | None = None
    in_stock: bool | None = None
    url: str | None = None
    recorded_at: datetime | None = None


class ImportRequest(BaseModel):
    source: str = "external_app"
    records: list[ImportRecord] = Field(min_length=1)


class ImportResponse(BaseModel):
    import_id: uuid.UUID
    records_count: int
    matched_count: int
    unmatched_count: int


class ImportLogResponse(BaseModel):
    id: uuid.UUID
    source: str
    records_count: int
    matched_count: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
