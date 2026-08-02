from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    phone: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password_hash: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    password_hash: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int