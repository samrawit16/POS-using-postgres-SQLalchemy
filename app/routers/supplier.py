from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.schemas.common import INT4_MAX, PathId
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services import supplier as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[SupplierRead], dependencies=[Depends(require_manager)])
def list_suppliers(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_suppliers(db, skip=skip, limit=limit)


@router.get("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(require_manager)])
def get_supplier(supplier_id: PathId, db: Session = Depends(get_db)):
    return svc.get_supplier(db, supplier_id)


@router.post("/", response_model=SupplierRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_manager)])
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    return svc.create_supplier(db, data)


@router.put("/{supplier_id}", response_model=SupplierRead, dependencies=[Depends(require_manager)])
def update_supplier(supplier_id: PathId, data: SupplierUpdate, db: Session = Depends(get_db)):
    return svc.update_supplier(db, supplier_id, data)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_supplier(supplier_id: PathId, db: Session = Depends(get_db)):
    svc.delete_supplier(db, supplier_id)
