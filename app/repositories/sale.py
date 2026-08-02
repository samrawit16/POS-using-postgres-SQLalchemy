from sqlalchemy.orm import Session

from app.models.sale import Sale


class SaleRepository:
    def __init__(self):
        self.model = Sale

    def get(self, db: Session, id: int):
        return db.get(Sale, id)

    def get_all(self, db: Session):
        return db.query(Sale).all()

    def create(self, db: Session, data: dict):
        obj = Sale(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Sale, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Sale):
        db.delete(db_obj)
        db.commit()


sale_repository = SaleRepository()