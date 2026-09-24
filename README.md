# POS API (FastAPI + SQLAlchemy + PostgreSQL)

Point-of-sale backend with JWT authentication, role-based access control, and a test suite
that runs on SQLite (default) or real PostgreSQL.

## Quick start

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt                       # add requirements-dev.txt to run the tests

cp .env.example .env                                  # then edit .env (never commit it)
python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste the output as SECRET_KEY

python init_db.py                                     # create tables (also happens on app start)
python create_admin.py                                # create the first admin (prompts; no public sign-up)
uvicorn app.main:app --reload                         # http://127.0.0.1:8000/docs
```

The app **refuses to start** if `DATABASE_URL` is missing, or `SECRET_KEY` is missing / shorter than
32 bytes / a known placeholder. No database schema changes were made, so an existing database keeps working.

## Authentication

```bash
# 1. log in (form-encoded, so Swagger's "Authorize" button works too)
curl -d "username=admin&password=YOUR_PASSWORD" http://127.0.0.1:8000/auth/login
# -> {"access_token": "...", "token_type": "bearer"}

# 2. send the token on every request
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/products/
```

| Endpoint | Purpose |
|---|---|
| `POST /auth/login` | username + password -> 30 min bearer token (configurable) |
| `GET /auth/me` | who am I |
| `POST /auth/change-password` | change own password; all older tokens stop working |

## Roles

| Resource | admin | manager | cashier |
|---|:-:|:-:|:-:|
| Users (all operations) | yes | - | - |
| Suppliers (all operations) | yes | yes | - |
| Categories, products, inventory: read | yes | yes | yes |
| Categories, products, inventory: create/update/delete | yes | yes | - |
| Customers: read / create / update | yes | yes | yes (health field hidden, see below) |
| Customers: delete | yes | yes | - |
| Sales, sale items, payments, receipts: read / create | yes | yes | yes (own sales only) |
| Sales, sale items, payments, receipts: update / delete | yes | yes | - |

* Cashiers can only create sales as themselves and only add items/payments/receipts to **their own** sales.
* Cashiers never see, and cannot set, a customer's `medical_conditions`.
* The system always keeps at least one active admin (the last one can't be deleted, demoted or deactivated).

## What is protected

* **Passwords**: Argon2id; clients send `password`, the hash is never accepted from or returned to a client;
  12-128 chars with a letter and a digit. Hashes are upgraded automatically at login if parameters change.
* **Tokens**: signed JWT, algorithm pinned, `exp`/`iat`/`sub` required. Tokens are re-checked against the DB on
  every request, so deactivating a user, changing a role, or changing a password takes effect immediately.
* **Brute force**: 5 failed logins per username+IP -> 5 minute lockout (429). Unknown usernames cost the same work
  as real ones, and error messages are identical, so usernames can't be enumerated.
* **Default deny**: every router requires a valid token; a test fails if any endpoint is reachable without one.
* **Input validation**: lengths match the DB columns, money is non-negative with the right precision, quantities are
  positive, ids are bounded, PATCH-style updates can't null out required fields, list endpoints are paginated
  (`?skip=&limit=`, max 500).
* **Error hygiene**: constraint violations return a clean 409 (details are logged server-side only).
* **HTTP**: security headers, CORS only for origins you list, `/docs` and `/openapi.json` disabled when
  `ENVIRONMENT=production`, HSTS in production.

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                   # SQLite, ~15 s
pytest --cov=app --cov-report=term-missing

# against real PostgreSQL (database name MUST contain "test": tables are dropped and recreated)
TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/pos_test pytest
```

## Before going to production

1. `ENVIRONMENT=production`, a fresh random `SECRET_KEY`, and `?sslmode=require` on `DATABASE_URL` for remote databases.
2. Serve behind HTTPS (nginx/Caddy/cloud load balancer). Behind a proxy, configure it to pass the client IP
   (uvicorn `--proxy-headers --forwarded-allow-ips=<proxy ip>`) or the login lockout will see every user as the proxy.
3. The login lockout is in-process memory: with several workers/containers use a shared limiter (Redis or your proxy/WAF).
4. Use a least-privilege PostgreSQL user for the app (no superuser / no DDL if you manage the schema yourself).
5. Adopt Alembic for schema changes: `create_all` only creates missing tables, it never alters existing ones.
6. Tokens live 30 min and there is no refresh/logout endpoint; add refresh tokens + a deny-list if you need them.

## Behaviour worth knowing about (unchanged from the original code)

* Sale `total_amount`, item `total_price` etc. are **supplied by the client** and not recomputed or reconciled with
  payments; stock (`inventory.quantity`) is not decremented when items are sold.
* Deleting a customer/category/supplier that other rows point at sets those rows' link to `NULL` instead of blocking
  the delete. Deleting a user with sales, or a product with sale items/inventory, is blocked (409).
