from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .common import Id, PatchModel, PositiveMoney12, Str20


class PaymentBase(BaseModel):
    sale_id: Id
    payment_method: Str20
    amount: PositiveMoney12
    status: Str20 = "completed"
    paid_at: datetime | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(PatchModel):
    nullable_fields = frozenset({"paid_at"})

    sale_id: Id | None = None
    payment_method: Str20 | None = None
    amount: PositiveMoney12 | None = None
    status: Str20 | None = None
    paid_at: datetime | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
