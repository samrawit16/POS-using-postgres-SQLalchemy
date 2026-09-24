from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import user_repository
from app.security import (
    burn_password_check,
    hash_password,
    needs_rehash,
    verify_password,
)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return the user if the credentials are right, else None.

    Unknown usernames still cost one hash verification, so response timing does
    not reveal which usernames exist.
    """
    user = user_repository.get_by_username(db, username.strip())
    if user is None:
        burn_password_check(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if needs_rehash(user.password_hash):  # transparently upgrade old hash parameters
        user.password_hash = hash_password(password)
        db.commit()
        db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if current_password == new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    user.password_hash = hash_password(new_password)
    db.commit()
