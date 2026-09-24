from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.models.user import User
from app.schemas.common import INT4_MAX, PathId
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate
from app.services import payment as svc

# Every route requires a valid token; the per-route guards below decide which roles may call it.
router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[PaymentRead], dependencies=[Depends(require_staff)])
def list_payments(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_payments(db, skip=skip, limit=limit)


@router.get("/{payment_id}", response_model=PaymentRead, dependencies=[Depends(require_staff)])
def get_payment(payment_id: PathId, db: Session = Depends(get_db)):
    return svc.get_payment(db, payment_id)


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentCreate, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.create_payment(db, data, actor)


@router.put("/{payment_id}", response_model=PaymentRead, dependencies=[Depends(require_manager)])
def update_payment(payment_id: PathId, data: PaymentUpdate, db: Session = Depends(get_db)):
    return svc.update_payment(db, payment_id, data)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_payment(payment_id: PathId, db: Session = Depends(get_db)):
    svc.delete_payment(db, payment_id)
