from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.models.user import User
from app.schemas.common import INT4_MAX, PathId
from app.schemas.sale_item import SaleItemCreate, SaleItemRead, SaleItemUpdate
from app.services import sale_item as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/sale-items", tags=["sale-items"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[SaleItemRead], dependencies=[Depends(require_staff)])
def list_sale_items(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_sale_items(db, skip=skip, limit=limit)


@router.get("/{sale_item_id}", response_model=SaleItemRead, dependencies=[Depends(require_staff)])
def get_sale_item(sale_item_id: PathId, db: Session = Depends(get_db)):
    return svc.get_sale_item(db, sale_item_id)


@router.post("/", response_model=SaleItemRead, status_code=status.HTTP_201_CREATED)
def create_sale_item(data: SaleItemCreate, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.create_sale_item(db, data, actor)


@router.put("/{sale_item_id}", response_model=SaleItemRead, dependencies=[Depends(require_manager)])
def update_sale_item(sale_item_id: PathId, data: SaleItemUpdate, db: Session = Depends(get_db)):
    return svc.update_sale_item(db, sale_item_id, data)


@router.delete("/{sale_item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_sale_item(sale_item_id: PathId, db: Session = Depends(get_db)):
    svc.delete_sale_item(db, sale_item_id)
