from datetime import date

from pydantic import BaseModel, ConfigDict

from .common import Id, PatchModel, Quantity, Str100


class InventoryBase(BaseModel):
    product_id: Id
    quantity: Quantity = 0
    reorder_level: Quantity = 10
    batch_number: Str100 | None = None
    expiry_date: date | None = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(PatchModel):
    nullable_fields = frozenset({"batch_number", "expiry_date"})

    product_id: Id | None = None
    quantity: Quantity | None = None
    reorder_level: Quantity | None = None
    batch_number: Str100 | None = None
    expiry_date: date | None = None


class InventoryRead(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
