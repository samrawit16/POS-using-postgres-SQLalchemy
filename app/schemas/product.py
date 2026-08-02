from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    generic_name: str | None = None
    description: str | None = None
    sku: str
    barcode: str | None = None
    price: Decimal
    cost: Decimal = Decimal("0")
    expiry_date: date | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    generic_name: str | None = None
    description: str | None = None
    sku: str | None = None
    barcode: str | None = None
    price: Decimal | None = None
    cost: Decimal | None = None
    expiry_date: date | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int