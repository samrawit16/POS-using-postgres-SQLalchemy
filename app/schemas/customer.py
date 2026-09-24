from datetime import date

from pydantic import BaseModel, ConfigDict

from .common import LongText, LowerEmail, PatchModel, Str20, Str100, Str255


class CustomerBase(BaseModel):
    first_name: Str100
    last_name: Str100
    email: str | None = None
    phone: Str20 | None = None
    date_of_birth: date | None = None
    medical_conditions: LongText | None = None
    insurance_provider: Str255 | None = None


class CustomerCreate(CustomerBase):
    email: LowerEmail | None = None


class CustomerUpdate(PatchModel):
    nullable_fields = frozenset(
        {"email", "phone", "date_of_birth", "medical_conditions", "insurance_provider"}
    )

    first_name: Str100 | None = None
    last_name: Str100 | None = None
    email: LowerEmail | None = None
    phone: Str20 | None = None
    date_of_birth: date | None = None
    medical_conditions: LongText | None = None
    insurance_provider: Str255 | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
