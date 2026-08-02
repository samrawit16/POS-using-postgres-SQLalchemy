from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self):
        self.model = User

    def get(self, db: Session, id: int):
        return db.get(User, id)

    def get_all(self, db: Session):
        return db.query(User).all()

    def create(self, db: Session, data: dict):
        obj = User(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: User, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: User):
        db.delete(db_obj)
        db.commit()


user_repository = UserRepository()