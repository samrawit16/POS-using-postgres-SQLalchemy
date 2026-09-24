from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.schemas.common import INT4_MAX, PathId
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services import product as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[ProductRead], dependencies=[Depends(require_staff)])
def list_products(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_products(db, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductRead, dependencies=[Depends(require_staff)])
def get_product(product_id: PathId, db: Session = Depends(get_db)):
    return svc.get_product(db, product_id)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_manager)])
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return svc.create_product(db, data)


@router.put("/{product_id}", response_model=ProductRead, dependencies=[Depends(require_manager)])
def update_product(product_id: PathId, data: ProductUpdate, db: Session = Depends(get_db)):
    return svc.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_product(product_id: PathId, db: Session = Depends(get_db)):
    svc.delete_product(db, product_id)
