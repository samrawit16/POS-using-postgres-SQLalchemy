from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import is_privileged
from app.models.user import User
from app.repositories.sale import sale_repository
from app.repositories.customer import customer_repository
from app.repositories.user import user_repository
from app.schemas.sale import SaleCreate, SaleUpdate


def get_sale(db: Session, id: int):
    sale = sale_repository.get(db, id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    return sale


def list_sales(db: Session, skip: int = 0, limit: int = 100):
    return sale_repository.get_all(db, skip=skip, limit=limit)


def create_sale(db: Session, data: SaleCreate, actor: User):
    if not is_privileged(actor) and data.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create sales for yourself",
        )
    if data.customer_id:
        customer = customer_repository.get(db, data.customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
    user = user_repository.get(db, data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return sale_repository.create(db, data.model_dump())


def update_sale(db: Session, sale_id: int, data: SaleUpdate):
    sale = get_sale(db, sale_id)
    update_data = data.model_dump(exclude_unset=True)
    if "customer_id" in update_data and update_data["customer_id"]:
        customer = customer_repository.get(db, update_data["customer_id"])
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
    if "user_id" in update_data and update_data["user_id"]:
        user = user_repository.get(db, update_data["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    return sale_repository.update(db, sale, update_data)


def delete_sale(db: Session, sale_id: int):
    sale = get_sale(db, sale_id)
    sale_repository.delete(db, sale)