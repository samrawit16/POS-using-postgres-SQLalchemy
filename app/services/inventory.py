from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.inventory import inventory_repository
from app.repositories.product import product_repository
from app.schemas.inventory import InventoryCreate, InventoryUpdate


def get_inventory(db: Session, id: int):
    inventory = inventory_repository.get(db, id)
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found"
        )
    return inventory


def list_inventory(db: Session, skip: int = 0, limit: int = 100):
    return inventory_repository.get_all(db, skip=skip, limit=limit)


def create_inventory(db: Session, data: InventoryCreate):
    product = product_repository.get(db, data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    existing = db.query(inventory_repository.model).filter(
        inventory_repository.model.product_id == data.product_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory already exists for this product"
        )
    return inventory_repository.create(db, data.model_dump())


def update_inventory(db: Session, inventory_id: int, data: InventoryUpdate):
    inventory = get_inventory(db, inventory_id)
    update_data = data.model_dump(exclude_unset=True)
    if "product_id" in update_data and update_data["product_id"]:
        product = product_repository.get(db, update_data["product_id"])
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
    return inventory_repository.update(db, inventory, update_data)


def delete_inventory(db: Session, inventory_id: int):
    inventory = get_inventory(db, inventory_id)
    inventory_repository.delete(db, inventory)