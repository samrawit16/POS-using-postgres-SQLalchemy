from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.sale_item import sale_item_repository
from app.repositories.sale import sale_repository
from app.repositories.product import product_repository
from app.schemas.sale_item import SaleItemCreate, SaleItemUpdate


def get_sale_item(db: Session, id: int):
    sale_item = sale_item_repository.get(db, id)
    if not sale_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale item not found"
        )
    return sale_item


def list_sale_items(db: Session):
    return sale_item_repository.get_all(db)


def create_sale_item(db: Session, data: SaleItemCreate):
    sale = sale_repository.get(db, data.sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    product = product_repository.get(db, data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return sale_item_repository.create(db, data.model_dump())


def update_sale_item(db: Session, sale_item_id: int, data: SaleItemUpdate):
    sale_item = get_sale_item(db, sale_item_id)
    update_data = data.model_dump(exclude_unset=True)
    if "sale_id" in update_data and update_data["sale_id"]:
        sale = sale_repository.get(db, update_data["sale_id"])
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
    if "product_id" in update_data and update_data["product_id"]:
        product = product_repository.get(db, update_data["product_id"])
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
    return sale_item_repository.update(db, sale_item, update_data)


def delete_sale_item(db: Session, sale_item_id: int):
    sale_item = get_sale_item(db, sale_item_id)
    sale_item_repository.delete(db, sale_item)