from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .common import Id, Money12, PatchModel


class SaleBase(BaseModel):
    customer_id: Id | None = None
    user_id: Id
    prescription_id: Id | None = None
    tax_amount: Money12 = Decimal("0")
    discount_amount: Money12 = Decimal("0")
    total_amount: Money12 = Decimal("0")


class SaleCreate(SaleBase):
    pass


class SaleUpdate(PatchModel):
    nullable_fields = frozenset({"customer_id", "prescription_id"})

    customer_id: Id | None = None
    user_id: Id | None = None
    prescription_id: Id | None = None
    tax_amount: Money12 | None = None
    discount_amount: Money12 | None = None
    total_amount: Money12 | None = None


class SaleRead(SaleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_date: datetime
