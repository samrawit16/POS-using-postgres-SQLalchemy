from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.login_throttle import login_throttle
from app.models.user import User
from app.schemas.user import ChangePassword, Token, UserRead
from app.security import create_access_token
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_BAD_LOGIN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Exchange username + password for a short-lived bearer token."""
    key = (form.username.strip().lower(), request.client.host if request.client else "unknown")

    wait = login_throttle.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )

    user = auth_service.authenticate_user(db, form.username, form.password)
    if user is None:
        login_throttle.record_failure(key)
        raise _BAD_LOGIN
    if not user.is_active:  # only reachable with the correct password
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    login_throttle.reset(key)
    return Token(access_token=create_access_token(user.id, user.password_hash))


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change your own password. Tokens issued before the change stop working."""
    auth_service.change_password(db, current_user, data.current_password, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
