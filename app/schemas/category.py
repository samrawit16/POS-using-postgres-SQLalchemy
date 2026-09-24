from pydantic import BaseModel, ConfigDict

from .common import Id, LongText, PatchModel, Str100


class CategoryBase(BaseModel):
    name: Str100
    description: LongText | None = None
    parent_category_id: Id | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(PatchModel):
    nullable_fields = frozenset({"description", "parent_category_id"})

    name: Str100 | None = None
    description: LongText | None = None
    parent_category_id: Id | None = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
