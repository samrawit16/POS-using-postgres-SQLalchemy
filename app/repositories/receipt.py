from app.models.receipt import Receipt

from .base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    pass


receipt_repository = ReceiptRepository(Receipt)
