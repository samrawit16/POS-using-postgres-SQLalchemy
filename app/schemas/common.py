"""Shared field types. Limits mirror the DB column definitions so bad input is
rejected with a 422 instead of blowing up inside PostgreSQL as a 500."""
from decimal import Decimal
from typing import Annotated, ClassVar

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints, model_validator

INT4_MAX = 2_147_483_647


def _s(max_length: int):
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)]


Str20, Str50, Str100, Str255 = _s(20), _s(50), _s(100), _s(255)
LongText = _s(10_000)
ReceiptText = _s(100_000)

Id = Annotated[int, Field(gt=0, le=INT4_MAX)]
Quantity = Annotated[int, Field(ge=0, le=INT4_MAX)]
PositiveQuantity = Annotated[int, Field(gt=0, le=INT4_MAX)]

Money10 = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Money12 = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveMoney12 = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


def _lower_email(v: str) -> str:
    if len(v) > 255:
        raise ValueError("email is too long")
    return v.lower()


LowerEmail = Annotated[EmailStr, AfterValidator(_lower_email)]


class PatchModel(BaseModel):
    """Base for *Update schemas: fields may be omitted, but a field that is
    NOT NULL in the database may not be explicitly set to null."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _no_explicit_null(self):
        bad = sorted(
            f
            for f in self.model_fields_set
            if f not in self.nullable_fields and getattr(self, f) is None
        )
        if bad:
            raise ValueError(f"{', '.join(bad)} cannot be null")
        return self


# For path parameters: an id above int4 would make PostgreSQL raise "integer out of range".
from fastapi import Path  # noqa: E402

PathId = Annotated[int, Path(gt=0, le=INT4_MAX)]
