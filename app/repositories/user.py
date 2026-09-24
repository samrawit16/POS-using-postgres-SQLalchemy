from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.roles import Role

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def get_by_username(self, db: Session, username: str) -> User | None:
        return db.scalars(select(User).where(func.lower(User.username) == username.lower())).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.scalars(select(User).where(func.lower(User.email) == email.lower())).first()

    def count_active_admins(self, db: Session) -> int:
        return db.scalar(
            select(func.count()).select_from(User).where(
                User.role == Role.admin.value, User.is_active.is_(True)
            )
        )


user_repository = UserRepository(User)
