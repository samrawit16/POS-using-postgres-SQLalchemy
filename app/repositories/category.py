from app.models.category import Category

from .base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    pass


category_repository = CategoryRepository(Category)
