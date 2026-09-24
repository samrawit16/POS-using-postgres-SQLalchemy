from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .common import Id, Money10, PatchModel, PositiveQuantity


class SaleItemBase(BaseModel):
    sale_id: Id
    product_id: Id
    quantity: PositiveQuantity
    unit_price: Money10
    discount_amount: Money10 = Decimal("0")
    total_price: Money10


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemUpdate(PatchModel):
    sale_id: Id | None = None
    product_id: Id | None = None
    quantity: PositiveQuantity | None = None
    unit_price: Money10 | None = None
    discount_amount: Money10 | None = None
    total_price: Money10 | None = None


class SaleItemRead(SaleItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
