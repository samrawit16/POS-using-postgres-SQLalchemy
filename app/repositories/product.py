from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def __init__(self):
        self.model = Product

    def get(self, db: Session, id: int):
        return db.get(Product, id)

    def get_all(self, db: Session):
        return db.query(Product).all()

    def create(self, db: Session, data: dict):
        obj = Product(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Product, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Product):
        db.delete(db_obj)
        db.commit()


product_repository = ProductRepository()