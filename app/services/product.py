from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.product import product_repository
from app.repositories.category import category_repository
from app.repositories.supplier import supplier_repository
from app.schemas.product import ProductCreate, ProductUpdate


def get_product(db: Session, id: int):
    product = product_repository.get(db, id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


def list_products(db: Session, skip: int = 0, limit: int = 100):
    return product_repository.get_all(db, skip=skip, limit=limit)


def create_product(db: Session, data: ProductCreate):
    if data.category_id:
        category = category_repository.get(db, data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    if data.supplier_id:
        supplier = supplier_repository.get(db, data.supplier_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
    return product_repository.create(db, data.model_dump())


def update_product(db: Session, product_id: int, data: ProductUpdate):
    product = get_product(db, product_id)
    update_data = data.model_dump(exclude_unset=True)
    if "category_id" in update_data and update_data["category_id"]:
        category = category_repository.get(db, update_data["category_id"])
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    if "supplier_id" in update_data and update_data["supplier_id"]:
        supplier = supplier_repository.get(db, update_data["supplier_id"])
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
    return product_repository.update(db, product, update_data)


def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    product_repository.delete(db, product)