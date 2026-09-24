from app.models.sale import Sale

from .base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    pass


sale_repository = SaleRepository(Sale)
