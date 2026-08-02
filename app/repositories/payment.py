from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self):
        self.model = Payment

    def get(self, db: Session, id: int):
        return db.get(Payment, id)

    def get_all(self, db: Session):
        return db.query(Payment).all()

    def create(self, db: Session, data: dict):
        obj = Payment(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Payment, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Payment):
        db.delete(db_obj)
        db.commit()


payment_repository = PaymentRepository()