from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    sale_id: int
    payment_method: str
    amount: Decimal
    status: str = "completed"
    paid_at: datetime | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    sale_id: int | None = None
    payment_method: str | None = None
    amount: Decimal | None = None
    status: str | None = None
    paid_at: datetime | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int