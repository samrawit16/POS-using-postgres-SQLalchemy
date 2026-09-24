from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.schemas.common import INT4_MAX, PathId
from app.schemas.inventory import InventoryCreate, InventoryRead, InventoryUpdate
from app.services import inventory as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[InventoryRead], dependencies=[Depends(require_staff)])
def list_inventory(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_inventory(db, skip=skip, limit=limit)


@router.get("/{inventory_id}", response_model=InventoryRead, dependencies=[Depends(require_staff)])
def get_inventory(inventory_id: PathId, db: Session = Depends(get_db)):
    return svc.get_inventory(db, inventory_id)


@router.post("/", response_model=InventoryRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_manager)])
def create_inventory(data: InventoryCreate, db: Session = Depends(get_db)):
    return svc.create_inventory(db, data)


@router.put("/{inventory_id}", response_model=InventoryRead, dependencies=[Depends(require_manager)])
def update_inventory(inventory_id: PathId, data: InventoryUpdate, db: Session = Depends(get_db)):
    return svc.update_inventory(db, inventory_id, data)


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_inventory(inventory_id: PathId, db: Session = Depends(get_db)):
    svc.delete_inventory(db, inventory_id)
