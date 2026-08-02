from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.category import category_repository
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_category(db: Session, id: int):
    category = category_repository.get(db, id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


def list_categories(db: Session):
    return category_repository.get_all(db)


def create_category(db: Session, data: CategoryCreate):
    if data.parent_category_id:
        parent = category_repository.get(db, data.parent_category_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
    return category_repository.create(db, data.model_dump())


def update_category(db: Session, category_id: int, data: CategoryUpdate):
    category = get_category(db, category_id)
    update_data = data.model_dump(exclude_unset=True)
    if "parent_category_id" in update_data and update_data["parent_category_id"]:
        parent = category_repository.get(db, update_data["parent_category_id"])
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
    return category_repository.update(db, category, update_data)


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    category_repository.delete(db, category)