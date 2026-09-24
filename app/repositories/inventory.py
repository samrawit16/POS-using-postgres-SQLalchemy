from app.models.inventory import Inventory

from .base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    pass


inventory_repository = InventoryRepository(Inventory)
