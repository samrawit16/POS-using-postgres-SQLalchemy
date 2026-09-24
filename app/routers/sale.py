from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.models.user import User
from app.schemas.common import INT4_MAX, PathId
from app.schemas.sale import SaleCreate, SaleRead, SaleUpdate
from app.services import sale as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/sales", tags=["sales"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[SaleRead], dependencies=[Depends(require_staff)])
def list_sales(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_sales(db, skip=skip, limit=limit)


@router.get("/{sale_id}", response_model=SaleRead, dependencies=[Depends(require_staff)])
def get_sale(sale_id: PathId, db: Session = Depends(get_db)):
    return svc.get_sale(db, sale_id)


@router.post("/", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(data: SaleCreate, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.create_sale(db, data, actor)


@router.put("/{sale_id}", response_model=SaleRead, dependencies=[Depends(require_manager)])
def update_sale(sale_id: PathId, data: SaleUpdate, db: Session = Depends(get_db)):
    return svc.update_sale(db, sale_id, data)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_sale(sale_id: PathId, db: Session = Depends(get_db)):
    svc.delete_sale(db, sale_id)
