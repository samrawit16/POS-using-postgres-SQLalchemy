from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sale_item import SaleItemCreate, SaleItemRead, SaleItemUpdate
from app.services.sale_item import list_sale_items, get_sale_item, create_sale_item, update_sale_item, delete_sale_item

router = APIRouter(prefix="/sale-items", tags=["sale-items"])


@router.get("/", response_model=list[SaleItemRead])
def list_sale_items(db: Session = Depends(get_db)):
    return list_sale_items(db)


@router.get("/{sale_item_id}", response_model=SaleItemRead)
def get_sale_item(sale_item_id: int, db: Session = Depends(get_db)):
    return get_sale_item(db, sale_item_id)


@router.post("/", response_model=SaleItemRead, status_code=status.HTTP_201_CREATED)
def create_sale_item(data: SaleItemCreate, db: Session = Depends(get_db)):
    return create_sale_item(db, data)


@router.put("/{sale_item_id}", response_model=SaleItemRead)
def update_sale_item(sale_item_id: int, data: SaleItemUpdate, db: Session = Depends(get_db)):
    return update_sale_item(db, sale_item_id, data)


@router.delete("/{sale_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale_item(sale_item_id: int, db: Session = Depends(get_db)):
    delete_sale_item(db, sale_item_id)