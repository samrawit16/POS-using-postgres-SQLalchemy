from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import user_repository
from app.roles import Role
from app.schemas.user import UserCreate, UserUpdate
from app.security import hash_password


def get_user(db: Session, id: int):
    user = user_repository.get(db, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100):
    return user_repository.get_all(db, skip=skip, limit=limit)


def _ensure_unique(db: Session, *, username: str | None, email: str | None, exclude_id: int | None = None):
    if username:
        other = user_repository.get_by_username(db, username)
        if other and other.id != exclude_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if email:
        other = user_repository.get_by_email(db, email)
        if other and other.id != exclude_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")


def _ensure_not_last_admin(db: Session, user: User):
    """Never allow the system to end up with zero active admins."""
    if (
        user.role == Role.admin.value
        and user.is_active
        and user_repository.count_active_admins(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove, demote or deactivate the last active admin",
        )


def create_user(db: Session, data: UserCreate):
    _ensure_unique(db, username=data.username, email=data.email)
    payload = data.model_dump(exclude={"password"})
    payload["role"] = data.role.value
    payload["password_hash"] = hash_password(data.password)
    return user_repository.create(db, payload)


def update_user(db: Session, user_id: int, data: UserUpdate):
    user = get_user(db, user_id)
    update_data = data.model_dump(exclude_unset=True)

    _ensure_unique(db, username=update_data.get("username"), email=update_data.get("email"), exclude_id=user.id)

    if "role" in update_data:
        update_data["role"] = update_data["role"].value
    loses_admin = update_data.get("role", user.role) != Role.admin.value or update_data.get(
        "is_active", user.is_active
    ) is False
    if loses_admin:
        _ensure_not_last_admin(db, user)

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    return user_repository.update(db, user, update_data)


def delete_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    _ensure_not_last_admin(db, user)
    user_repository.delete(db, user)
