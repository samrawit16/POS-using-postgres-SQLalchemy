from app.models.payment import Payment

from .base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    pass


payment_repository = PaymentRepository(Payment)
