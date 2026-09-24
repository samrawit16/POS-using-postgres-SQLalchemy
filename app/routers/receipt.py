from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.models.user import User
from app.schemas.common import INT4_MAX, PathId
from app.schemas.receipt import ReceiptCreate, ReceiptRead, ReceiptUpdate
from app.services import receipt as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/receipts", tags=["receipts"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[ReceiptRead], dependencies=[Depends(require_staff)])
def list_receipts(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_receipts(db, skip=skip, limit=limit)


@router.get("/{receipt_id}", response_model=ReceiptRead, dependencies=[Depends(require_staff)])
def get_receipt(receipt_id: PathId, db: Session = Depends(get_db)):
    return svc.get_receipt(db, receipt_id)


@router.post("/", response_model=ReceiptRead, status_code=status.HTTP_201_CREATED)
def create_receipt(data: ReceiptCreate, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.create_receipt(db, data, actor)


@router.put("/{receipt_id}", response_model=ReceiptRead, dependencies=[Depends(require_manager)])
def update_receipt(receipt_id: PathId, data: ReceiptUpdate, db: Session = Depends(get_db)):
    return svc.update_receipt(db, receipt_id, data)


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_receipt(receipt_id: PathId, db: Session = Depends(get_db)):
    svc.delete_receipt(db, receipt_id)
