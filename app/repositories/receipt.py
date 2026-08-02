from sqlalchemy.orm import Session

from app.models.receipt import Receipt


class ReceiptRepository:
    def __init__(self):
        self.model = Receipt

    def get(self, db: Session, id: int):
        return db.get(Receipt, id)

    def get_all(self, db: Session):
        return db.query(Receipt).all()

    def create(self, db: Session, data: dict):
        obj = Receipt(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Receipt, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Receipt):
        db.delete(db_obj)
        db.commit()


receipt_repository = ReceiptRepository()