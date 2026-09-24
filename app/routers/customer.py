from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager, require_staff
from app.models.user import User
from app.schemas.common import INT4_MAX, PathId
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services import customer as svc

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(get_current_user)])


# Customer records hold personal + health data: staff can read/create/update them,
# but `medical_conditions` is redacted for (and cannot be set by) cashiers.
@router.get("/", response_model=list[CustomerRead])
def list_customers(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return [svc.present_customer(c, actor) for c in svc.list_customers(db, skip=skip, limit=limit)]


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: PathId, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.present_customer(svc.get_customer(db, customer_id), actor)


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, actor: User = Depends(require_staff), db: Session = Depends(get_db)):
    return svc.present_customer(svc.create_customer(db, data, actor), actor)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: PathId,
    data: CustomerUpdate,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return svc.present_customer(svc.update_customer(db, customer_id, data, actor), actor)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_manager)])
def delete_customer(customer_id: PathId, db: Session = Depends(get_db)):
    svc.delete_customer(db, customer_id)
