from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.payment import payment_repository
from app.repositories.sale import sale_repository
from app.schemas.payment import PaymentCreate, PaymentUpdate


def get_payment(db: Session, id: int):
    payment = payment_repository.get(db, id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment


def list_payments(db: Session):
    return payment_repository.get_all(db)


def create_payment(db: Session, data: PaymentCreate):
    sale = sale_repository.get(db, data.sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    return payment_repository.create(db, data.model_dump())


def update_payment(db: Session, payment_id: int, data: PaymentUpdate):
    payment = get_payment(db, payment_id)
    update_data = data.model_dump(exclude_unset=True)
    if "sale_id" in update_data and update_data["sale_id"]:
        sale = sale_repository.get(db, update_data["sale_id"])
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
    return payment_repository.update(db, payment, update_data)


def delete_payment(db: Session, payment_id: int):
    payment = get_payment(db, payment_id)
    payment_repository.delete(db, payment)