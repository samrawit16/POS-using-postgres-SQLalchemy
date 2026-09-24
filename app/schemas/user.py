import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.roles import Role

from .common import LowerEmail, PatchModel, Str20, Str100

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,100}$")


def validate_password_strength(v: str) -> str:
    if not (12 <= len(v) <= 128):
        raise ValueError("password must be between 12 and 128 characters")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("password must contain at least one letter and one digit")
    return v


def _username(v: str) -> str:
    v = v.strip()
    if not USERNAME_RE.match(v):
        raise ValueError("username must be 3-100 chars: letters, digits, '_', '.', '-'")
    return v.lower()


class UserBase(BaseModel):
    username: str
    email: str
    first_name: Str100
    last_name: Str100
    role: Role
    phone: Str20 | None = None
    is_active: bool = True


class UserCreate(UserBase):
    """Clients send a plain `password`; it is hashed server-side and never stored or returned."""

    username: str = Field(min_length=3, max_length=100)
    email: LowerEmail
    password: str = Field(repr=False)

    _v_username = field_validator("username")(_username)
    _v_password = field_validator("password")(validate_password_strength)


class UserUpdate(PatchModel):
    nullable_fields = frozenset({"phone"})

    username: str | None = Field(default=None, min_length=3, max_length=100)
    email: LowerEmail | None = None
    password: str | None = Field(default=None, repr=False)
    first_name: Str100 | None = None
    last_name: Str100 | None = None
    role: Role | None = None
    phone: Str20 | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def _check_username(cls, v):
        return None if v is None else _username(v)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v):
        return None if v is None else validate_password_strength(v)


class UserRead(UserBase):
    """Never includes the password or its hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class ChangePassword(BaseModel):
    current_password: str = Field(repr=False)
    new_password: str = Field(repr=False)

    _v_new = field_validator("new_password")(validate_password_strength)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
