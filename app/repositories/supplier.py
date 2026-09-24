from app.models.supplier import Supplier

from .base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    pass


supplier_repository = SupplierRepository(Supplier)
