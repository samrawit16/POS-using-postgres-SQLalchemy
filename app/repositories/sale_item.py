from app.models.sale_item import SaleItem

from .base import BaseRepository


class SaleItemRepository(BaseRepository[SaleItem]):
    pass


sale_item_repository = SaleItemRepository(SaleItem)
