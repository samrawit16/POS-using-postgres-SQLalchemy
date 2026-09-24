from enum import Enum


class Role(str, Enum):
    admin = "admin"      # everything, including user management
    manager = "manager"  # catalogue/inventory/suppliers + edit or delete transactions
    cashier = "cashier"  # ring up sales; read the catalogue
