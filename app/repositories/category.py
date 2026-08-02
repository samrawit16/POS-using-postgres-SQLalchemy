from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    def __init__(self):
        self.model = Category

    def get(self, db: Session, id: int):
        return db.get(Category, id)

    def get_all(self, db: Session):
        return db.query(Category).all()

    def create(self, db: Session, data: dict):
        obj = Category(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Category, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Category):
        db.delete(db_obj)
        db.commit()


category_repository = CategoryRepository()