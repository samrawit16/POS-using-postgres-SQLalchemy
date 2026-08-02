from sqlalchemy.orm import Session

from app.models.sale_item import SaleItem


class SaleItemRepository:
    def __init__(self):
        self.model = SaleItem

    def get(self, db: Session, id: int):
        return db.get(SaleItem, id)

    def get_all(self, db: Session):
        return db.query(SaleItem).all()

    def create(self, db: Session, data: dict):
        obj = SaleItem(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: SaleItem, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: SaleItem):
        db.delete(db_obj)
        db.commit()


sale_item_repository = SaleItemRepository()