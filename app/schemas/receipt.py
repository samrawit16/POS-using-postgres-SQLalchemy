from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReceiptBase(BaseModel):
    sale_id: int
    receipt_number: str
    receipt_data: str
    emailed_at: datetime | None = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(BaseModel):
    sale_id: int | None = None
    receipt_number: str | None = None
    receipt_data: str | None = None
    emailed_at: datetime | None = None


class ReceiptRead(ReceiptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int