from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .common import Id, PatchModel, ReceiptText, Str50


class ReceiptBase(BaseModel):
    sale_id: Id
    receipt_number: Str50
    receipt_data: ReceiptText
    emailed_at: datetime | None = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(PatchModel):
    nullable_fields = frozenset({"emailed_at"})

    sale_id: Id | None = None
    receipt_number: Str50 | None = None
    receipt_data: ReceiptText | None = None
    emailed_at: datetime | None = None


class ReceiptRead(ReceiptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
