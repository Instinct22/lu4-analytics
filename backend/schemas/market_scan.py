import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScanPrice(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Literal["adena", "master coin"]

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower().replace("_", " ")
        if normalized in {"mastercoin", "mc"}:
            return "master coin"
        return normalized


class ScanRecord(BaseModel):
    action: Literal["buy", "sell"]
    name: str = Field(min_length=1, max_length=256)
    item: str = Field(min_length=1, max_length=512)
    count: int = Field(gt=0)
    price: ScanPrice
    timestamp: datetime


class ScanBatchRequest(BaseModel):
    records: list[ScanRecord] = Field(min_length=1)


class ScanResponse(BaseModel):
    id: uuid.UUID
    matched: bool


class ScanBatchResponse(BaseModel):
    saved_count: int
    matched_count: int
