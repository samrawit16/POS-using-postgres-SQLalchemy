from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .common import Id, LongText, Money10, PatchModel, Str100, Str255


class ProductBase(BaseModel):
    name: Str255
    generic_name: Str255 | None = None
    description: LongText | None = None
    sku: Str100
    barcode: Str100 | None = None
    price: Money10
    cost: Money10 = Decimal("0")
    expiry_date: date | None = None
    category_id: Id | None = None
    supplier_id: Id | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(PatchModel):
    nullable_fields = frozenset(
        {"generic_name", "description", "barcode", "expiry_date", "category_id", "supplier_id"}
    )

    name: Str255 | None = None
    generic_name: Str255 | None = None
    description: LongText | None = None
    sku: Str100 | None = None
    barcode: Str100 | None = None
    price: Money10 | None = None
    cost: Money10 | None = None
    expiry_date: date | None = None
    category_id: Id | None = None
    supplier_id: Id | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
