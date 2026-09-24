import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.config import get_settings
from app.database import Base, engine
from app.routers import (
    auth_router,
    categories_router,
    customers_router,
    inventory_router,
    payments_router,
    products_router,
    receipts_router,
    sale_items_router,
    sales_router,
    suppliers_router,
    users_router,
)

logger = logging.getLogger("pos")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates missing tables only (never alters existing ones). For schema
    # changes on a live database, use a migration tool such as Alembic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="POS API",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs and the schema are for development; hidden in production.
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,  # we use bearer tokens, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")  # responses contain personal data
    if settings.ENVIRONMENT == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # Duplicate SKU/email/receipt number, deleting a row that is still referenced, etc.
    # Log the details server-side; never echo SQL or constraint names to the client.
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={"detail": "Conflict with existing data (duplicate value or record still in use)"},
    )


app.include_router(auth_router)
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


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
