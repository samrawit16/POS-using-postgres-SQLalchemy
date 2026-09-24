from app.models.product import Product

from .base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    pass


product_repository = ProductRepository(Product)
