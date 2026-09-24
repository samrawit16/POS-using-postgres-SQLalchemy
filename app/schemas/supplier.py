from pydantic import BaseModel, ConfigDict

from .common import LongText, LowerEmail, PatchModel, Str20, Str50, Str100


class SupplierBase(BaseModel):
    name: Str100
    contact_person: Str100 | None = None
    email: str | None = None
    phone: Str20 | None = None
    address: LongText | None = None
    tax_id: Str50 | None = None


class SupplierCreate(SupplierBase):
    email: LowerEmail | None = None


class SupplierUpdate(PatchModel):
    nullable_fields = frozenset({"contact_person", "email", "phone", "address", "tax_id"})

    name: Str100 | None = None
    contact_person: Str100 | None = None
    email: LowerEmail | None = None
    phone: Str20 | None = None
    address: LongText | None = None
    tax_id: Str50 | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
