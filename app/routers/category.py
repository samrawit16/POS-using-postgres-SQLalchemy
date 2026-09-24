from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.schemas.common import INT4_MAX, PathId
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import category as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/categories", tags=["categories"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[CategoryRead], dependencies=[Depends(require_staff)])
def list_categories(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_categories(db, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoryRead, dependencies=[Depends(require_staff)])
def get_category(category_id: PathId, db: Session = Depends(get_db)):
    return svc.get_category(db, category_id)


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_manager)])
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return svc.create_category(db, data)


@router.put("/{category_id}", response_model=CategoryRead, dependencies=[Depends(require_manager)])
def update_category(category_id: PathId, data: CategoryUpdate, db: Session = Depends(get_db)):
    return svc.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_category(category_id: PathId, db: Session = Depends(get_db)):
    svc.delete_category(db, category_id)
