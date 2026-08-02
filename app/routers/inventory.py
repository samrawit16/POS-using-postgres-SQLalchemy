from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.inventory import InventoryCreate, InventoryRead, InventoryUpdate
from app.services.inventory import list_inventory, get_inventory, create_inventory, update_inventory, delete_inventory

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryRead])
def list_inventory(db: Session = Depends(get_db)):
    return list_inventory(db)


@router.get("/{inventory_id}", response_model=InventoryRead)
def get_inventory(inventory_id: int, db: Session = Depends(get_db)):
    return get_inventory(db, inventory_id)


@router.post("/", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
def create_inventory(data: InventoryCreate, db: Session = Depends(get_db)):
    return create_inventory(db, data)


@router.put("/{inventory_id}", response_model=InventoryRead)
def update_inventory(inventory_id: int, data: InventoryUpdate, db: Session = Depends(get_db)):
    return update_inventory(db, inventory_id, data)


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(inventory_id: int, db: Session = Depends(get_db)):
    delete_inventory(db, inventory_id)