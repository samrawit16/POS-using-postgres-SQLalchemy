from datetime import date

from pydantic import BaseModel, ConfigDict


class InventoryBase(BaseModel):
    product_id: int
    quantity: int = 0
    reorder_level: int = 10
    batch_number: str | None = None
    expiry_date: date | None = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    product_id: int | None = None
    quantity: int | None = None
    reorder_level: int | None = None
    batch_number: str | None = None
    expiry_date: date | None = None


class InventoryRead(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int