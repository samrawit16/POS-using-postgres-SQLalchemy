from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import is_privileged
from app.models.user import User
from app.repositories.customer import customer_repository
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate


def present_customer(customer, actor: User) -> CustomerRead:
    """Health data is only visible to admins/managers; cashiers get it blanked."""
    out = CustomerRead.model_validate(customer)
    if not is_privileged(actor):
        out = out.model_copy(update={"medical_conditions": None})
    return out


def _guard_medical(actor: User, medical_conditions_supplied: bool):
    if medical_conditions_supplied and not is_privileged(actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers may set medical conditions",
        )


def get_customer(db: Session, id: int):
    customer = customer_repository.get(db, id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer


def list_customers(db: Session, skip: int = 0, limit: int = 100):
    return customer_repository.get_all(db, skip=skip, limit=limit)


def create_customer(db: Session, data: CustomerCreate, actor: User):
    _guard_medical(actor, data.medical_conditions is not None)
    return customer_repository.create(db, data.model_dump())


def update_customer(db: Session, customer_id: int, data: CustomerUpdate, actor: User):
    update_data = data.model_dump(exclude_unset=True)
    _guard_medical(actor, "medical_conditions" in update_data)
    customer = get_customer(db, customer_id)
    return customer_repository.update(db, customer, update_data)


def delete_customer(db: Session, customer_id: int):
    customer = get_customer(db, customer_id)
    customer_repository.delete(db, customer)