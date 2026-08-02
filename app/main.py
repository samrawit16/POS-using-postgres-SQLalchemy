# import models
# from database import Base, enigne
# from routers import products

# Base.metadata.create_all(blind=enigne)
# app = FastAPI(title = "Pos API", version = "1")

# app.include_router(products.router)

from fastapi import FastAPI

from app import models
from app.database import Base, engine
from app.routers import (
    categories_router,
    suppliers_router,
    products_router,
    inventory_router,
    customers_router,
    users_router,
    sales_router,
    sale_items_router,
    payments_router,
    receipts_router,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="POS API", version="1.0.0")

app.include_router(categories_router)
app.include_router(suppliers_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(customers_router)
app.include_router(users_router)
app.include_router(sales_router)
app.include_router(sale_items_router)
app.include_router(payments_router)
app.include_router(receipts_router)