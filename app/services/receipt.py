from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.receipt import receipt_repository
from app.repositories.sale import sale_repository
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate


def get_receipt(db: Session, id: int):
    receipt = receipt_repository.get(db, id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    return receipt


def list_receipts(db: Session):
    return receipt_repository.get_all(db)


def create_receipt(db: Session, data: ReceiptCreate):
    sale = sale_repository.get(db, data.sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    existing = db.query(receipt_repository.model).filter(
        receipt_repository.model.sale_id == data.sale_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt already exists for this sale"
        )
    return receipt_repository.create(db, data.model_dump())


def update_receipt(db: Session, receipt_id: int, data: ReceiptUpdate):
    receipt = get_receipt(db, receipt_id)
    update_data = data.model_dump(exclude_unset=True)
    if "sale_id" in update_data and update_data["sale_id"]:
        sale = sale_repository.get(db, update_data["sale_id"])
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
    return receipt_repository.update(db, receipt, update_data)


def delete_receipt(db: Session, receipt_id: int):
    receipt = get_receipt(db, receipt_id)
    receipt_repository.delete(db, receipt)