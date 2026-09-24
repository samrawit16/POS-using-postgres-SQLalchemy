"""Object-level permission checks shared by services."""
from fastapi import HTTPException, status

from app.dependencies import is_privileged
from app.models.sale import Sale
from app.models.user import User


def ensure_can_modify_sale(actor: User, sale: Sale) -> None:
    """Cashiers may only add lines/payments/receipts to their own sales.

    Admins and managers may act on any sale.
    """
    if not is_privileged(actor) and sale.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own sales",
        )
