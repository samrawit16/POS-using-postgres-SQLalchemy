from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.schemas.common import INT4_MAX, PathId
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user as svc

# User management is admin-only, on every route.
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_current_user), Depends(require_admin)])


@router.get("/", response_model=list[UserRead])
def list_users(
    skip: int = Query(0, ge=0, le=INT4_MAX),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return svc.list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: PathId, db: Session = Depends(get_db)):
    return svc.get_user(db, user_id)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    return svc.create_user(db, data)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: PathId, data: UserUpdate, db: Session = Depends(get_db)):
    return svc.update_user(db, user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: PathId, db: Session = Depends(get_db)):
    svc.delete_user(db, user_id)
