from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SaleBase(BaseModel):
    customer_id: int | None = None
    user_id: int
    prescription_id: int | None = None
    tax_amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    customer_id: int | None = None
    user_id: int | None = None
    prescription_id: int | None = None
    tax_amount: Decimal | None = None
    discount_amount: Decimal | None = None
    total_amount: Decimal | None = None


class SaleRead(SaleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_date: datetime