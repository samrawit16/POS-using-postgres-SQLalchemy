"""Authentication + authorisation dependencies."""
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.roles import Role
from app.security import decode_access_token, fingerprint_matches

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    decoded = decode_access_token(token)
    if decoded is None:
        raise _CREDENTIALS_ERROR
    user_id, token_fp = decoded

    user = db.get(User, user_id)
    # Re-checked against the DB on every request so that deactivating a user or
    # changing their password takes effect immediately, not when the token expires.
    if user is None or not user.is_active or not fingerprint_matches(token_fp, user.password_hash):
        raise _CREDENTIALS_ERROR
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    allowed = {r.value for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user

    return checker


require_staff = require_roles(Role.admin, Role.manager, Role.cashier)
require_manager = require_roles(Role.admin, Role.manager)
require_admin = require_roles(Role.admin)


def is_privileged(user: User) -> bool:
    return user.role in (Role.admin.value, Role.manager.value)
